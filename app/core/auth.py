"""
 * Authentication and Authorization Utilities
 *
 * This file contains authentication and authorization functions for
 * protecting API endpoints with role-based access control (RBAC).
 *
 * Public Functions:
 *    get_current_user(credentials: HTTPAuthorizationCredentials, db: Client) --> dict
 *        Gets the current authenticated user from JWT token
 *    get_optional_user(credentials: Optional[HTTPAuthorizationCredentials], db: Client) --> Optional[dict]
 *        Gets current user if authenticated, otherwise returns None
 *    require_role(allowed_roles: List[UserRole]) --> Callable
 *        Factory function that returns a dependency requiring specific roles
 *    require_admin_dashboard_access(current_user: dict) --> dict
 *        Requires admin dashboard access (admin or policy working group)
 *    require_admin(current_user: dict) --> dict
 *        Requires admin role only - full access to create, edit, delete
 *    require_suggestion_manager(current_user: dict) --> dict
 *        Requires admin or policy working group - can manage suggestions
 *    require_public_or_admin(current_user: Optional[dict]) --> Optional[dict]
 *        Allows both public and authenticated users
 *
 * @author: ASA Policy App Development Team
 * @date: January 2026
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Callable
from app.core.database import get_db, get_service_db
from app.models.schemas import UserRole
from supabase import Client

security = HTTPBearer()

# Roles that can access admin dashboard
ADMIN_DASHBOARD_ROLES: List[str] = ["admin", "policy_working_group"]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Client = Depends(get_db)
) -> dict:
    """
    Get current authenticated user from Supabase Auth token
    
    Args:
        credentials: HTTP Bearer token credentials from request header
        db: Supabase database client
        
    Returns:
        dict: Dictionary containing user id, email, role, and metadata
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token: str = credentials.credentials
    
    try:
        # Verify token with Supabase Auth
        user_response = db.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = user_response.user
        
        # Get user role from users table
        user_data = db.table("users").select("*").eq("id", user.id).execute()
        
        if user_data.data:
            role: str = user_data.data[0].get("role", "public")
        else:
            # If user doesn't exist in users table, create with default role
            # Note: Users should be registered by admin, but if they somehow exist in Auth
            # but not in users table, default to public
            role = "public"
            db.table("users").insert({
                "id": user.id,
                "email": user.email,
                "role": role
            }).execute()
        
        return {
            "id": user.id,
            "email": user.email,
            "role": role,
            "user_metadata": user.user_metadata
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Client = Depends(get_db)
) -> Optional[dict]:
    """
    Get current user if authenticated, otherwise return None
    
    This function is useful for endpoints that work for both
    authenticated and unauthenticated users.
    
    Args:
        credentials: Optional HTTP Bearer token credentials
        db: Supabase database client
        
    Returns:
        Optional[dict]: User dictionary if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(allowed_roles: List[UserRole]) -> Callable:
    """
    Dependency factory to require specific roles
    
    Args:
        allowed_roles: List of UserRole enums that are allowed
        
    Returns:
        Callable: FastAPI dependency function that checks user role
    """
    async def role_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        """
        Internal function that checks if user has required role
        
        Args:
            current_user: Current authenticated user dictionary
            
        Returns:
            dict: Current user if role is allowed
            
        Raises:
            HTTPException: 403 if user role is not in allowed_roles
        """
        user_role: str = current_user.get("role", "public")
        
        # Check if user role is in allowed roles
        if user_role not in [role.value for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}"
            )
        
        return current_user
    
    return role_checker


async def require_admin_dashboard_access(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Require admin dashboard access - only admin or policy working group
    
    Public users cannot access admin dashboard
    
    Args:
        current_user: Current authenticated user dictionary
        
    Returns:
        dict: Current user if they have dashboard access
        
    Raises:
        HTTPException: 403 if user is not admin or policy working group
    """
    user_role: str = current_user.get("role", "public")
    
    if user_role not in ADMIN_DASHBOARD_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only admin and policy working group members can access the admin dashboard."
        )
    
    return current_user


# Common role dependencies
async def require_admin(
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """
    Require admin role only - full access to create, edit, delete policies/bylaws
    
    Args:
        current_user: Current authenticated user dictionary
        
    Returns:
        dict: Current user if they are admin
        
    Raises:
        HTTPException: 403 if user is not admin
    """
    return current_user


async def require_suggestion_manager(
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.POLICY_WORKING_GROUP]))
) -> dict:
    """
    Require admin or policy working group - can manage suggestions
    
    Args:
        current_user: Current authenticated user dictionary
        
    Returns:
        dict: Current user if they are admin or policy working group
        
    Raises:
        HTTPException: 403 if user is not admin or policy working group
    """
    return current_user


async def require_public_or_admin(
    current_user: Optional[dict] = Depends(get_optional_user)
) -> Optional[dict]:
    """
    Allow both public and authenticated users
    
    Args:
        current_user: Optional authenticated user dictionary
        
    Returns:
        Optional[dict]: User dictionary if authenticated, None if public
    """
    return current_user
