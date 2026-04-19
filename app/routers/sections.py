"""
 * Sections API Routes
 *
 * Manage policy "sections" (e.g., 1, 2, 3) and their display names.
 *
 * - Public can list sections (used by public site and admin UI).
 * - Admin can create sections and rename them.
 *
 * @author: ASA Policy App Development Team
 * @date: April 2026
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime

from supabase import Client

from app.core.database import get_db, get_service_db
from app.core.auth import require_admin
from app.core.config import settings
from app.models.schemas import SectionCreate, SectionUpdate, SectionResponse

router = APIRouter()


def convert_section_from_db(row: dict) -> dict:
    return {
        "id": str(row.get("id")),
        "key": row.get("key", ""),
        "name": row.get("name", ""),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


@router.get("/", response_model=List[SectionResponse])
async def list_sections(db: Client = Depends(get_db)) -> List[SectionResponse]:
    try:
        response = db.table(settings.SECTIONS_TABLE).select("*").order("key").execute()
        return [convert_section_from_db(row) for row in (response.data or [])]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sections: {str(e)}")


@router.post("/", response_model=SectionResponse, status_code=201)
async def create_section(
    section: SectionCreate,
    current_user: dict = Depends(require_admin),
    db: Client = Depends(get_service_db),
) -> SectionResponse:
    try:
        existing = db.table(settings.SECTIONS_TABLE).select("id").eq("key", section.key).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Section key already exists")

        now = datetime.utcnow().isoformat()
        payload = {
            "key": section.key,
            "name": section.name,
            "created_at": now,
            "updated_at": now,
            "created_by": current_user.get("id"),
            "updated_by": current_user.get("id"),
        }
        response = db.table(settings.SECTIONS_TABLE).insert(payload).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create section")
        return convert_section_from_db(response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating section: {str(e)}")


@router.put("/{section_key}", response_model=SectionResponse)
async def update_section(
    section_key: str,
    update: SectionUpdate,
    current_user: dict = Depends(require_admin),
    db: Client = Depends(get_service_db),
) -> SectionResponse:
    try:
        existing = db.table(settings.SECTIONS_TABLE).select("*").eq("key", section_key).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Section not found")

        update_data = {}
        if update.name is not None:
            update_data["name"] = update.name

        if not update_data:
            return convert_section_from_db(existing.data[0])

        update_data["updated_at"] = datetime.utcnow().isoformat()
        update_data["updated_by"] = current_user.get("id")

        response = db.table(settings.SECTIONS_TABLE).update(update_data).eq("key", section_key).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update section")
        return convert_section_from_db(response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating section: {str(e)}")


@router.delete("/{section_key}", status_code=204)
async def delete_section(
    section_key: str,
    current_user: dict = Depends(require_admin),
    db: Client = Depends(get_service_db),
) -> None:
    """
    Delete a section (admin only).

    Only allowed if there are zero policies currently assigned to that section key.
    """
    try:
        existing = db.table(settings.SECTIONS_TABLE).select("id").eq("key", section_key).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Section not found")

        policies = db.table(settings.POLICIES_TABLE).select("id").eq("section", section_key).execute()
        policy_count = len(policies.data or [])
        if policy_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete section '{section_key}' because it has {policy_count} policy/policies"
            )

        db.table(settings.SECTIONS_TABLE).delete().eq("key", section_key).execute()
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting section: {str(e)}")

