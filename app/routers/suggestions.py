"""
 * Suggestion API Routes
 *
 * This file contains all API endpoints for managing suggestions in the
 * ASA Policy Management System. Suggestions can be created by public users,
 * and managed (viewed, deleted) by admin and policy working group members.
 *
 * Public Functions:
 *    convert_suggestion_from_db(row: dict) --> dict
 *        Converts a database row to suggestion response format
 *    get_suggestions(status: Optional[SuggestionStatus], policy_id: Optional[str],
 *      bylaw_id: Optional[str], limit: int, offset: int, current_user: dict, db: Client) --> List[SuggestionResponse]
 *        Gets all suggestions with optional filtering (admin or policy working group)
 *    create_suggestion(suggestion: SuggestionCreate, db: Client) --> SuggestionResponse
 *        Creates a new suggestion (public access)
 *    delete_suggestion(suggestion_id: str, current_user: dict, db: Client) --> None
 *        Deletes a suggestion (admin or policy working group)
 *
 * @author: ASA Policy App Development Team
 * @date: January 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.core.database import get_db, get_service_db
from app.core.auth import require_admin, require_suggestion_manager, get_optional_user
from app.models.schemas import (
    SuggestionCreate, SuggestionUpdate, SuggestionResponse, SuggestionStatus
)
from app.core.config import settings
from supabase import Client
from datetime import datetime

router = APIRouter()


def convert_suggestion_from_db(row: dict, policy_info: Optional[dict] = None, bylaw_info: Optional[dict] = None) -> dict:
    """
    Convert database row to suggestion response format
    
    Args:
        row: Dictionary containing suggestion data from database
        policy_info: Optional dictionary with policy information {policy_id, policy_name}
        bylaw_info: Optional dictionary with bylaw information {bylaw_number, bylaw_title}
    """
    result = {
        "id": str(row.get("id")),
        "policy_id": row.get("policy_id"),
        "bylaw_id": row.get("bylaw_id"),
        "suggestion": row.get("suggestion", ""),
        "status": row.get("status", "pending"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "policy_id_text": None,
        "policy_name": None,
        "bylaw_number": None,
        "bylaw_title": None
    }
    
    # Add policy information if available
    if policy_info:
        result["policy_id_text"] = policy_info.get("policy_id")
        result["policy_name"] = policy_info.get("policy_name")
    
    # Add bylaw information if available
    if bylaw_info:
        result["bylaw_number"] = bylaw_info.get("bylaw_number")
        result["bylaw_title"] = bylaw_info.get("bylaw_title")
    
    return result


@router.get("/", response_model=List[SuggestionResponse])
async def get_suggestions(
    status: Optional[SuggestionStatus] = Query(None, description="Filter by status"),
    policy_id: Optional[str] = Query(None, description="Filter by policy_id (TEXT like '1.1.1')"),
    bylaw_id: Optional[str] = Query(None, description="Filter by bylaw ID (UUID)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_suggestion_manager),  # Admin or policy working group
    db: Client = Depends(get_service_db)
):
    """
    Get all suggestions (admin or policy working group)
    
    Args:
        status: Optional status filter
        policy_id: Policy identifier (TEXT like "1.1.1") - will be converted to UUID
        bylaw_id: Bylaw UUID
        limit: Maximum number of results
        offset: Pagination offset
        current_user: Current authenticated user
        db: Supabase database client
        
    Returns:
        List[SuggestionResponse]: List of suggestions
    """
    try:
        query = db.table(settings.SUGGESTIONS_TABLE).select("*")
        
        # Apply filters
        if status:
            query = query.eq("status", status.value)
        if policy_id:
            # Convert policy_id (TEXT) to UUID for filtering
            policy_check = db.table(settings.POLICIES_TABLE).select("id").eq("policy_id", policy_id).execute()
            if policy_check.data:
                policy_uuid = policy_check.data[0].get("id")
                query = query.eq("policy_id", policy_uuid)
            else:
                # Policy not found, return empty list
                return []
        if bylaw_id:
            query = query.eq("bylaw_id", bylaw_id)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        # Order by creation date (newest first)
        query = query.order("created_at", desc=True)
        
        response = query.execute()
        
        # Collect all unique policy and bylaw UUIDs from suggestions
        policy_uuids = set()
        bylaw_uuids = set()
        for row in response.data:
            if row.get("policy_id"):
                policy_uuids.add(row.get("policy_id"))
            if row.get("bylaw_id"):
                bylaw_uuids.add(row.get("bylaw_id"))
        
        # Fetch policy information for all policy UUIDs
        policy_map = {}
        if policy_uuids:
            policies_response = db.table(settings.POLICIES_TABLE).select("id, policy_id, name").in_("id", list(policy_uuids)).execute()
            for policy in policies_response.data:
                policy_map[policy.get("id")] = {
                    "policy_id": policy.get("policy_id"),
                    "policy_name": policy.get("name")
                }
        
        # Fetch bylaw information for all bylaw UUIDs
        bylaw_map = {}
        if bylaw_uuids:
            bylaws_response = db.table(settings.BYLAWS_TABLE).select("id, number, title").in_("id", list(bylaw_uuids)).execute()
            for bylaw in bylaws_response.data:
                bylaw_map[bylaw.get("id")] = {
                    "bylaw_number": bylaw.get("number"),
                    "bylaw_title": bylaw.get("title")
                }
        
        # Convert suggestions with policy/bylaw information
        suggestions = []
        for row in response.data:
            policy_info = policy_map.get(row.get("policy_id")) if row.get("policy_id") else None
            bylaw_info = bylaw_map.get(row.get("bylaw_id")) if row.get("bylaw_id") else None
            suggestions.append(convert_suggestion_from_db(row, policy_info, bylaw_info))
        
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching suggestions: {str(e)}")


@router.post("/", response_model=SuggestionResponse, status_code=201)
async def create_suggestion(
    suggestion: SuggestionCreate,
    db: Client = Depends(get_db)  # Public can create suggestions
):
    """Create a new suggestion (public access)"""
    try:
        # Validate that either policy_id or bylaw_id is provided
        if not suggestion.policy_id and not suggestion.bylaw_id:
            raise HTTPException(
                status_code=400,
                detail="Either policy_id or bylaw_id must be provided"
            )
        
        # Convert policy_id (TEXT) or bylaw_id to UUID for foreign key relationships
        policy_uuid = None
        bylaw_uuid = None
        
        # If policy_id is provided (TEXT like "1.1.1"), look up the UUID
        if suggestion.policy_id:
            policy_check = db.table(settings.POLICIES_TABLE).select("id").eq("policy_id", suggestion.policy_id).execute()
            if not policy_check.data:
                raise HTTPException(status_code=404, detail="Policy not found")
            policy_uuid = policy_check.data[0].get("id")  # Get UUID for foreign key
        
        # If bylaw_id is provided, verify it exists and get UUID
        # Note: bylaw_id in suggestions might be UUID or bylaw number - need to check schema
        # For now, assuming it's UUID (bylaws don't have a TEXT identifier like policies)
        if suggestion.bylaw_id:
            bylaw_check = db.table(settings.BYLAWS_TABLE).select("id").eq("id", suggestion.bylaw_id).execute()
            if not bylaw_check.data:
                raise HTTPException(status_code=404, detail="Bylaw not found")
            bylaw_uuid = bylaw_check.data[0].get("id")  # Get UUID for foreign key
        
        suggestion_data = {
            "policy_id": policy_uuid,  # Use UUID for foreign key
            "bylaw_id": bylaw_uuid,  # Use UUID for foreign key
            "suggestion": suggestion.suggestion,
            "status": suggestion.status.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = db.table(settings.SUGGESTIONS_TABLE).insert(suggestion_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create suggestion")
        
        return convert_suggestion_from_db(response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating suggestion: {str(e)}")


@router.delete("/{suggestion_id}", status_code=204)
async def delete_suggestion(
    suggestion_id: str,
    current_user: dict = Depends(require_suggestion_manager),  # Admin or policy working group
    db: Client = Depends(get_service_db)
):
    """Delete a suggestion (admin or policy working group)"""
    try:
        # Check if suggestion exists
        existing = db.table(settings.SUGGESTIONS_TABLE).select("*").eq("id", suggestion_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        # Delete suggestion
        db.table(settings.SUGGESTIONS_TABLE).delete().eq("id", suggestion_id).execute()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting suggestion: {str(e)}")
