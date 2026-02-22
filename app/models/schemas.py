"""
 * Pydantic Schemas for Request/Response Validation
 *
 * This file contains all Pydantic models used for request validation and
 * response serialization in the ASA Policy Management System API.
 *
 * Public Classes:
 *    PolicyStatus(Enum)
 *        Enumeration for policy status values (draft, approved)
 *    PolicyBase, PolicyCreate, PolicyUpdate, PolicyResponse
 *        Schemas for policy data validation and serialization
 *    BylawBase, BylawCreate, BylawUpdate, BylawResponse
 *        Schemas for bylaw data validation and serialization
 *    SuggestionStatus(Enum)
 *        Enumeration for suggestion status values
 *    SuggestionBase, SuggestionCreate, SuggestionUpdate, SuggestionResponse
 *        Schemas for suggestion data validation and serialization
 *    UserRole(Enum)
 *        Enumeration for user roles (public, admin, policy_working_group)
 *    UserBase, UserResponse
 *        Schemas for user data validation and serialization
 *
 * @author: ASA Policy App Development Team
 * @date: January 2026
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PolicyStatus(str, Enum):
    """Policy status enumeration"""
    DRAFT = "draft"
    APPROVED = "approved"


# Policy Schemas
class PolicyBase(BaseModel):
    """Base policy schema"""
    policy_id: str = Field(..., description="Policy identifier (e.g., '1.1.1')")
    policy_name: str = Field(..., description="Policy name")
    section: str = Field(..., description="Section number (1, 2, or 3)")
    policy_content: str = Field(default="", description="Policy content/text")
    status: PolicyStatus = Field(default=PolicyStatus.DRAFT, description="Policy status")


class PolicyCreate(PolicyBase):
    """Schema for creating a new policy"""
    pass


class PolicyUpdate(BaseModel):
    """Schema for updating a policy"""
    policy_name: Optional[str] = None
    section: Optional[str] = None
    policy_content: Optional[str] = None
    status: Optional[PolicyStatus] = None


class PolicyResponse(PolicyBase):
    """Schema for policy response"""
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True


# Bylaw Schemas
class BylawBase(BaseModel):
    """Base bylaw schema"""
    bylaw_number: int = Field(..., description="Bylaw number (whole number)", gt=0)
    bylaw_title: str = Field(..., description="Bylaw title")
    bylaw_content: str = Field(default="", description="Bylaw content/text")
    status: PolicyStatus = Field(default=PolicyStatus.DRAFT, description="Bylaw status")


class BylawCreate(BylawBase):
    """Schema for creating a new bylaw"""
    pass


class BylawUpdate(BaseModel):
    """Schema for updating a bylaw"""
    bylaw_number: Optional[int] = Field(None, gt=0)
    bylaw_title: Optional[str] = None
    bylaw_content: Optional[str] = None
    status: Optional[PolicyStatus] = None


class BylawResponse(BylawBase):
    """Schema for bylaw response"""
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True


# Suggestion Schemas
class SuggestionStatus(str, Enum):
    """Suggestion status enumeration"""
    PENDING = "pending"
    REVIEWED = "reviewed"
    IMPLEMENTED = "implemented"
    REJECTED = "rejected"


class SuggestionBase(BaseModel):
    """Base suggestion schema"""
    policy_id: Optional[str] = Field(None, description="Related policy ID")
    bylaw_id: Optional[str] = Field(None, description="Related bylaw ID")
    suggestion: str = Field(..., description="Suggestion text")
    status: SuggestionStatus = Field(default=SuggestionStatus.PENDING, description="Suggestion status")


class SuggestionCreate(SuggestionBase):
    """Schema for creating a new suggestion"""
    pass


class SuggestionUpdate(BaseModel):
    """Schema for updating a suggestion"""
    status: Optional[SuggestionStatus] = None
    suggestion: Optional[str] = None


class SuggestionResponse(SuggestionBase):
    """Schema for suggestion response"""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Additional fields for display (populated from related policy/bylaw)
    policy_id_text: Optional[str] = Field(None, description="Policy ID text (e.g., '1.1.1') if suggestion is for a policy")
    policy_name: Optional[str] = Field(None, description="Policy name if suggestion is for a policy")
    bylaw_number: Optional[int] = Field(None, description="Bylaw number if suggestion is for a bylaw")
    bylaw_title: Optional[str] = Field(None, description="Bylaw title if suggestion is for a bylaw")
    
    class Config:
        from_attributes = True


# User Schemas
class UserRole(str, Enum):
    """User role enumeration"""
    PUBLIC = "public"  # Public users - cannot access admin dashboard
    ADMIN = "admin"  # Full access to all operations
    POLICY_WORKING_GROUP = "policy_working_group"  # Can manage suggestions only


class UserBase(BaseModel):
    """Base user schema"""
    email: str
    name: Optional[str] = None
    role: UserRole = Field(default=UserRole.PUBLIC, description="User role")


class UserResponse(UserBase):
    """Schema for user response"""
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Search and Filter Schemas
class PolicySearchParams(BaseModel):
    """Parameters for policy search"""
    query: Optional[str] = None
    section: Optional[str] = None
    status: Optional[PolicyStatus] = None
    tags: Optional[List[str]] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class BylawSearchParams(BaseModel):
    """Parameters for bylaw search"""
    query: Optional[str] = None
    status: Optional[PolicyStatus] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# Policy Review Schemas
class ReviewStatus(str, Enum):
    """Review status enumeration"""
    CONFIRM = "confirm"
    NEEDS_WORK = "needs_work"


class PolicyReviewCreate(BaseModel):
    """Schema for creating a policy review"""
    review_status: ReviewStatus = Field(..., description="Review status: 'confirm' or 'needs_work'")


class PolicyReviewResponse(BaseModel):
    """Schema for policy review response"""
    numberOfPeople: int = Field(..., description="Number of people who submitted this review status")
    people: List[str] = Field(..., description="List of email addresses of people who submitted this review status")


class PolicyReviewsResponse(BaseModel):
    """Schema for all policy reviews response"""
    confirmed: PolicyReviewResponse = Field(..., description="Confirmed reviews")
    needs_work: PolicyReviewResponse = Field(..., description="Needs work reviews")
