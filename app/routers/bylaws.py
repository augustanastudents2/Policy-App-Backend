"""
 * Bylaw API Routes
 *
 * This file contains all API endpoints for managing bylaws in the
 * ASA Policy Management System. Bylaws can be created, read, updated,
 * and deleted by admins, while public users can only view approved bylaws.
 *
 * Public Functions:
 *    convert_bylaw_from_db(row: dict) --> dict
 *        Converts a database row to bylaw response format
 *    get_bylaws(status: Optional[PolicyStatus], search: Optional[str], 
 *      limit: int, offset: int, current_user: dict, db: Client) --> List[BylawResponse]
 *        Gets all bylaws with optional filtering (admin or policy_working_group only)
 *    get_approved_bylaws(search: Optional[str], db: Client) --> List[BylawResponse]
 *        Gets only approved bylaws (public access)
 *    get_approved_bylaw_by_id(bylaw_id: str, db: Client) --> BylawResponse
 *        Gets a single approved bylaw by ID (public access, only approved bylaws)
 *    approve_bylaw(bylaw_id: str, current_user: dict, db: Client) --> BylawResponse
 *        Approves a bylaw (admin only)
 *    create_bylaw(bylaw: BylawCreate, current_user: dict, db: Client) --> BylawResponse
 *        Creates a new bylaw (admin only)
 *    update_bylaw(bylaw_id: str, bylaw_update: BylawUpdate, 
 *      current_user: dict, db: Client) --> BylawResponse
 *        Updates an existing bylaw (admin only)
 *    delete_bylaw(bylaw_id: str, current_user: dict, db: Client) --> None
 *        Deletes a bylaw (admin only)
 *
 * @author: ASA Policy App Development Team
 * @date: January 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.core.database import get_db, get_service_db
from app.core.auth import require_admin, require_suggestion_manager
from app.models.schemas import (
    BylawCreate, BylawUpdate, BylawResponse, PolicyStatus
)
from app.core.config import settings
from supabase import Client
from datetime import datetime

router = APIRouter()


def convert_bylaw_from_db(row: dict) -> dict:
    """
    Convert database row to bylaw response format
    
    Maps database column names to API field names:
    - number (INTEGER) -> bylaw_number (int)
    - title -> bylaw_title
    - content -> bylaw_content
    
    Args:
        row: Dictionary containing bylaw data from database
        
    Returns:
        dict: Formatted bylaw dictionary with API field names
    """
    # Get number value - should be INTEGER in DB, but handle both int and string
    number_value = row.get("number", 0)
    try:
        # If it's already an int, use it; otherwise convert
        bylaw_number = int(number_value) if number_value is not None else 0
    except (ValueError, TypeError):
        bylaw_number = 0
    
    return {
        "id": str(row.get("id")),
        "bylaw_number": bylaw_number,  # Map number to bylaw_number (int)
        "bylaw_title": row.get("title", ""),  # Map title to bylaw_title
        "bylaw_content": row.get("content", ""),  # Map content to bylaw_content
        "status": row.get("status", "draft"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "created_by": row.get("created_by"),
        "updated_by": row.get("updated_by")
    }


@router.get("/", response_model=List[BylawResponse])
async def get_bylaws(
    status: Optional[PolicyStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_suggestion_manager),  # Admin or policy_working_group only
    db: Client = Depends(get_db)
) -> List[BylawResponse]:
    """
    Get all bylaws with optional filtering (admin or policy_working_group only)
    
    This endpoint is restricted to authenticated users with admin or policy_working_group roles.
    Public users should use the /approved endpoint to view only approved bylaws.
    
    Args:
        status: Optional status filter (draft, approved, archived, under_review)
        search: Optional search query to filter by title, number, or content
        limit: Maximum number of results to return (1-100)
        offset: Number of results to skip for pagination
        current_user: Current authenticated user (admin or policy_working_group)
        db: Supabase database client
        
    Returns:
        List[BylawResponse]: List of bylaw objects matching the filters
        
    Raises:
        HTTPException: 403 if user is not admin or policy_working_group, 500 if database error occurs
    """
    try:
        query = db.table(settings.BYLAWS_TABLE).select("*")
        
        # Apply filters
        if status:
            query = query.eq("status", status.value)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        # Order by number
        query = query.order("number")
        
        response = query.execute()
        
        # Filter by search term in Python if provided
        bylaws: List[dict] = [convert_bylaw_from_db(row) for row in response.data]
        if search:
            search_lower: str = search.lower()
            bylaws = [
                b for b in bylaws
                if search_lower in b.get("bylaw_title", "").lower()
                or search_lower in str(b.get("bylaw_number", "")).lower()
                or search_lower in b.get("bylaw_content", "").lower()
            ]
        
        return bylaws
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bylaws: {str(e)}")


@router.get("/approved", response_model=List[BylawResponse])
async def get_approved_bylaws(
    search: Optional[str] = Query(None, description="Search query"),
    db: Client = Depends(get_db)
) -> List[BylawResponse]:
    """
    Get only approved bylaws (public view)
    
    This endpoint is accessible without authentication and returns
    only bylaws with status "approved".
    
    Args:
        search: Optional search query to filter by title, number, or content
        db: Supabase database client
        
    Returns:
        List[BylawResponse]: List of approved bylaw objects
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        query = db.table(settings.BYLAWS_TABLE).select("*").eq("status", "approved")
        
        query = query.order("number")
        
        response = query.execute()
        
        # Filter by search term in Python if provided
        bylaws: List[dict] = [convert_bylaw_from_db(row) for row in response.data]
        if search:
            search_lower: str = search.lower()
            bylaws = [
                b for b in bylaws
                if search_lower in b.get("bylaw_title", "").lower()
                or search_lower in str(b.get("bylaw_number", "")).lower()
                or search_lower in b.get("bylaw_content", "").lower()
            ]
        
        return bylaws
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching approved bylaws: {str(e)}")


@router.get("/{bylaw_id}", response_model=BylawResponse)
async def get_approved_bylaw_by_id(
    bylaw_id: str,
    db: Client = Depends(get_db)
) -> BylawResponse:
    """
    Get a single approved bylaw by ID
    
    This endpoint only returns approved bylaws. Public users can access this
    endpoint to view approved bylaws. Non-approved bylaws will return 404.
    
    Args:
        bylaw_id: UUID of the bylaw to retrieve
        db: Supabase database client
        
    Returns:
        BylawResponse: Approved bylaw object with all details
        
    Raises:
        HTTPException: 404 if bylaw not found or not approved, 500 if database error occurs
    """
    try:
        # Only return approved bylaws
        response = db.table(settings.BYLAWS_TABLE).select("*").eq("id", bylaw_id).eq("status", "approved").execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Bylaw not found")
        
        return convert_bylaw_from_db(response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bylaw: {str(e)}")


@router.post("/", response_model=BylawResponse, status_code=201)
async def create_bylaw(
    bylaw: BylawCreate,
    current_user: dict = Depends(require_suggestion_manager),  # Admin or policy_working_group
    db: Client = Depends(get_service_db)  # Use service role for admin operations
) -> BylawResponse:
    """
    Create a new bylaw (admin and policy_working_group)
    
    Args:
        bylaw: BylawCreate object containing bylaw data
        current_user: Current authenticated user (admin or policy_working_group) 
        db: Supabase database client with service role
        
    Returns:
        BylawResponse: Created bylaw object
        
    Raises:
        HTTPException: 400 if bylaw number already exists, 500 if creation fails
    """
    try:
        # Map API field names to database column names
        # bylaw_number is already an integer from the schema
        bylaw_number = bylaw.bylaw_number
        
        # Check if bylaw number already exists
        existing = db.table(settings.BYLAWS_TABLE).select("*").eq("number", bylaw_number).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Bylaw number already exists")
        
        # Always create bylaws as draft - only admin can approve via approve endpoint
        bylaw_data: dict = {
            "number": bylaw_number,  # Store as INTEGER in DB
            "title": bylaw.bylaw_title,  # Map bylaw_title to title
            "content": bylaw.bylaw_content,  # Map bylaw_content to content
            "status": "draft",  # Always create as draft
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "created_by": current_user.get("id"),
            "updated_by": current_user.get("id")
        }
        
        response = db.table(settings.BYLAWS_TABLE).insert(bylaw_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create bylaw")
        
        return convert_bylaw_from_db(response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating bylaw: {str(e)}")


@router.put("/{bylaw_id}", response_model=BylawResponse)
async def update_bylaw(
    bylaw_id: str,
    bylaw_update: BylawUpdate,
    current_user: dict = Depends(require_suggestion_manager),  # Admin or policy_working_group
    db: Client = Depends(get_service_db)  # Use service role for operations
) -> BylawResponse:
    """
    Update a bylaw (admin or policy_working_group)
    
    Updated bylaws are automatically marked as "draft" status.
    Only admins can approve bylaws using the approve endpoint.
    
    Args:
        bylaw_id: UUID of the bylaw to update
        bylaw_update: BylawUpdate object containing fields to update
        current_user: Current authenticated user (admin or policy_working_group)
        db: Supabase database client with service role
        
    Returns:
        BylawResponse: Updated bylaw object (status will be "draft")
        
    Raises:
        HTTPException: 404 if bylaw not found, 500 if update fails
    """
    try:
        # Get existing bylaw
        existing = db.table(settings.BYLAWS_TABLE).select("*").eq("id", bylaw_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Bylaw not found")
        
        # Build update data - map API field names to database column names
        update_data: dict = {}
        if bylaw_update.bylaw_number is not None:
            update_data["number"] = bylaw_update.bylaw_number  # Map bylaw_number to number (INTEGER)
        if bylaw_update.bylaw_title is not None:
            update_data["title"] = bylaw_update.bylaw_title  # Map bylaw_title to title
        if bylaw_update.bylaw_content is not None:
            update_data["content"] = bylaw_update.bylaw_content  # Map bylaw_content to content
        
        # Always set status to DRAFT when bylaw is updated by policy_working_group or admin
        # Only admin can approve bylaws via the approve endpoint
        # This ensures that any update changes the bylaw back to draft
        update_data["status"] = "draft"
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        update_data["updated_by"] = current_user.get("id")
        
        response = db.table(settings.BYLAWS_TABLE).update(update_data).eq("id", bylaw_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update bylaw")
        
        return convert_bylaw_from_db(response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating bylaw: {str(e)}")


@router.put("/{bylaw_id}/approve", response_model=BylawResponse)
async def approve_bylaw(
    bylaw_id: str,
    current_user: dict = Depends(require_admin),  # Only admin can approve
    db: Client = Depends(get_service_db)  # Use service role for admin operations
) -> BylawResponse:
    """
    Approve a bylaw (admin only)
    
    Changes the bylaw status from "draft" to "approved".
    Only administrators can approve bylaws.
    
    Args:
        bylaw_id: UUID of the bylaw to approve
        current_user: Current authenticated admin user
        db: Supabase database client with service role
        
    Returns:
        BylawResponse: Approved bylaw object
        
    Raises:
        HTTPException: 404 if bylaw not found, 400 if already approved, 500 if update fails
    """
    try:
        # Get existing bylaw
        existing = db.table(settings.BYLAWS_TABLE).select("*").eq("id", bylaw_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Bylaw not found")
        
        existing_bylaw = existing.data[0]
        current_status = existing_bylaw.get("status", "draft")
        
        # Check if already approved
        if current_status == PolicyStatus.APPROVED.value:
            raise HTTPException(
                status_code=400,
                detail="Bylaw is already approved"
            )
        
        # Update status to approved
        update_data = {
            "status": PolicyStatus.APPROVED.value,
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": current_user.get("id")
        }
        
        response = db.table(settings.BYLAWS_TABLE).update(update_data).eq("id", bylaw_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to approve bylaw")
        
        return convert_bylaw_from_db(response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error approving bylaw: {str(e)}")


@router.delete("/{bylaw_id}", status_code=204)
async def delete_bylaw(
    bylaw_id: str,
    current_user: dict = Depends(require_admin),  # Require admin role
    db: Client = Depends(get_service_db)  # Use service role for admin operations
) -> None:
    """
    Delete a bylaw (admin only)
    
    Args:
        bylaw_id: UUID of the bylaw to delete
        current_user: Current authenticated admin user
        db: Supabase database client with service role
        
    Returns:
        None: 204 No Content on success
        
    Raises:
        HTTPException: 404 if bylaw not found, 500 if deletion fails
    """
    try:
        # Check if bylaw exists
        existing = db.table(settings.BYLAWS_TABLE).select("*").eq("id", bylaw_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Bylaw not found")
        
        # Delete bylaw
        db.table(settings.BYLAWS_TABLE).delete().eq("id", bylaw_id).execute()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting bylaw: {str(e)}")
