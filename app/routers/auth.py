"""
 * Authentication API Routes
 *
 * This file contains all API endpoints for user authentication and management
 * in the ASA Policy Management System. Handles login, registration, user
 * management, and role-based access control.
 *
 * Public Functions:
 *    login(login_data: LoginRequest, db: Client) --> LoginResponse
 *        Authenticates user and returns access token (admin or policy_working_group only)
 *    register(register_data: RegisterRequest, current_user: dict, db: Client) --> LoginResponse
 *        Registers a new user (admin only, assigns policy_working_group role)
 *    get_current_user_info(current_user: dict, db: Client) --> UserResponse
 *        Gets current authenticated user information
 *    logout(current_user: dict, db: Client) --> dict
 *        Logs out the current user
 *    get_all_users(current_user: dict, db: Client) --> List[UserResponse]
 *        Gets all users (admin only)
 *    update_user_role(user_id: str, role_data: UpdateUserRoleRequest,
 *      current_user: dict, db: Client) --> UserResponse
 *        Updates a user's role (admin only)
 *
 * @author: ASA Policy App Development Team
 * @date: January 2026
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.core.database import get_db, get_service_db
from app.core.auth import get_current_user, get_optional_user, require_admin
from app.models.schemas import UserResponse, UserRole
from app.core.config import settings
from supabase import Client

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class DeleteUserResponse(BaseModel):
    """Delete user response schema"""
    message: str
    deleted_user_id: str


class RegisterRequest(BaseModel):
    """Registration request schema"""
    email: EmailStr
    password: str
    name: Optional[str] = None


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: Client = Depends(get_db)
):
    """Login endpoint using Supabase Auth - Only admin, council, and policy working group can login"""
    try:
        # Sign in with Supabase Auth
        auth_response = db.auth.sign_in_with_password({
            "email": login_data.email,
            "password": login_data.password
        })
        
        if not auth_response or not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = auth_response.user
        
        # Check if session exists (may be None if email confirmation required)
        if not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not confirmed. Please check your email and verify your account."
            )
        
        access_token = auth_response.session.access_token
        
        # Get user role from users table - check by both id and email
        user_data = db.table(settings.USERS_TABLE).select("*").eq("id", user.id).execute()
        
        # If not found by id, try by email (in case of ID mismatch)
        if not user_data.data:
            user_data = db.table(settings.USERS_TABLE).select("*").eq("email", user.email).execute()
            # If found by email but ID doesn't match, update the ID
            if user_data.data:
                existing_user = user_data.data[0]
                # Update the user record to use the correct ID from Auth
                db.table(settings.USERS_TABLE).update({
                    "id": user.id
                }).eq("email", user.email).execute()
                user_data = db.table(settings.USERS_TABLE).select("*").eq("id", user.id).execute()
        
        if user_data.data:
            role = user_data.data[0].get("role", "public")
            name = user_data.data[0].get("name")
        else:
            # User doesn't exist in users table - try to create with public role
            # Handle case where user might already exist (race condition or email conflict)
            try:
                db.table(settings.USERS_TABLE).insert({
                    "id": user.id,
                    "email": user.email,
                    "role": "public",
                    "name": None
                }).execute()
                # Re-fetch to get the created user
                user_data = db.table(settings.USERS_TABLE).select("*").eq("id", user.id).execute()
                if user_data.data:
                    role = user_data.data[0].get("role", "public")
                    name = user_data.data[0].get("name")
                else:
                    role = "public"
                    name = None
            except Exception as insert_error:
                # If insert fails (e.g., duplicate email), try to fetch by email
                user_data = db.table(settings.USERS_TABLE).select("*").eq("email", user.email).execute()
                if user_data.data:
                    # Update the ID to match Auth user ID
                    db.table(settings.USERS_TABLE).update({
                        "id": user.id
                    }).eq("email", user.email).execute()
                    user_data = db.table(settings.USERS_TABLE).select("*").eq("id", user.id).execute()
                    if user_data.data:
                        role = user_data.data[0].get("role", "public")
                        name = user_data.data[0].get("name")
                    else:
                        role = "public"
                        name = None
                else:
                    # If we still can't find/create the user, default to public
                    role = "public"
                    name = None
            
            # Deny login since they have public role (or couldn't be created)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only admin and policy working group members can access the admin dashboard. Please contact an administrator to upgrade your account."
            )
        
        # Check if user has permission to access admin dashboard
        # Only admin and policy_working_group can login
        if role not in ["admin", "policy_working_group"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Your current role is '{role}'. Only admin and policy working group members can access the admin dashboard. Please contact an administrator to upgrade your account."
            )
        
        return {
            "access_token": access_token, # Delete this later before deployment
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": name,
                "role": role
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/register", response_model=LoginResponse)
async def register(
    register_data: RegisterRequest,
    current_user: dict = Depends(require_admin),  # Only admin can register users
    db: Client = Depends(get_service_db)  # Use service role for admin operations
):
    """
    Register a new user (admin only)
    
    Only administrators can register new users. New users are automatically
    assigned the 'policy_working_group' role, which allows them to access
    the admin dashboard and manage suggestions.
    
    Args:
        register_data: Registration request with email, password, and optional name
        current_user: Current authenticated admin user
        db: Supabase database client with service role
        
    Returns:
        LoginResponse: Access token and user information
        
    Raises:
        HTTPException: 400 if registration fails, 403 if not admin
    """
    try:
        # Create user with Supabase Auth ADMIN API so no confirmation email is sent.
        # This requires the service role key and marks the email as confirmed.
        auth_response = None
        try:
            admin_auth = db.auth.admin
            auth_response = admin_auth.create_user({
                "email": register_data.email,
                "password": register_data.password,
                "email_confirm": True,
                "user_metadata": {"name": register_data.name},
            })
        except Exception:
            # Fallback to raw HTTP if admin helper isn't available in this supabase client version
            import httpx

            url = settings.SUPABASE_URL.rstrip("/") + "/auth/v1/admin/users"
            headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "email": register_data.email,
                "password": register_data.password,
                "email_confirm": True,
                "user_metadata": {"name": register_data.name},
            }
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(url, headers=headers, json=payload)
                if r.status_code >= 400:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Registration failed: {r.text}",
                    )
                auth_response = type("AuthResp", (), {"user": type("User", (), r.json())})()
        
        if not auth_response or not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
        
        user = auth_response.user
        
        # Create user record in users table with policy_working_group role
        db.table(settings.USERS_TABLE).insert({
            "id": user.id,
            "email": user.email,
            "role": "policy_working_group",  # Default to policy_working_group role
            "name": register_data.name
        }).execute()
        
        # For admin-created users, we don't create a session here.
        # The user can log in normally with email/password immediately.
        access_token = ""
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": register_data.name,
                "role": "policy_working_group"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Get current authenticated user information"""
    # Get full user data from users table
    user_data = db.table(settings.USERS_TABLE).select("*").eq("id", current_user["id"]).execute()
    
    if user_data.data:
        user_record = user_data.data[0]
        return {
            "id": user_record["id"],
            "email": user_record["email"],
            "name": user_record.get("name"),
            "role": user_record.get("role", "public"),
            "created_at": user_record.get("created_at")
        }
    
    # Fallback to auth user data
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user.get("user_metadata", {}).get("name"),
        "role": current_user.get("role", "public"),
        "created_at": None
    }


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Logout endpoint"""
    try:
        # Sign out from Supabase Auth
        db.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        # Even if sign_out fails, return success
        return {"message": "Logged out successfully"}


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_service_db)  # Admin only
):
    """Get all users (admin only)"""
    # Check if user is admin (not council or policy_working_group)
    user_role = current_user.get("role", "public")
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    try:
        response = db.table(settings.USERS_TABLE).select("*").order("created_at", desc=True).execute()
        return [
            {
                "id": user["id"],
                "email": user["email"],
                "name": user.get("name"),
                "role": user.get("role", "public"),
                "created_at": user.get("created_at")
            }
            for user in response.data
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )


class UpdateUserRoleRequest(BaseModel):
    """Request schema for updating user role"""
    role: UserRole


@router.put("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    role_data: UpdateUserRoleRequest,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_service_db)  # Admin only
):
    """Update user role (admin only)"""
    # Check if current user is admin (not council or policy_working_group)
    user_role = current_user.get("role", "public")
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    try:
        # Update user role
        response = db.table(settings.USERS_TABLE).update({
            "role": role_data.role.value
        }).eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = response.data[0]
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "role": user.get("role", "public"),
            "created_at": user.get("created_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user role: {str(e)}"
        )


@router.delete("/users/{user_id}", status_code=200, response_model=DeleteUserResponse)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_service_db)  # Admin only
) -> DeleteUserResponse:
    """Delete a user (admin only)"""
    # Check if current user is admin (not council or policy_working_group)
    user_role = current_user.get("role", "public")
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    # Prevent deleting yourself
    if user_id == current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
    
    try:
        # Check if user exists
        user_check = db.table(settings.USERS_TABLE).select("*").eq("id", user_id).execute()
        if not user_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_to_delete = user_check.data[0]
        user_email = user_to_delete.get("email")

        # Delete from Supabase Auth first (prevents orphan auth accounts)
        auth_deleted = False
        try:
            admin_auth = getattr(getattr(db, "auth", None), "admin", None)
            if admin_auth and hasattr(admin_auth, "delete_user"):
                admin_auth.delete_user(user_id)
                auth_deleted = True
            else:
                import httpx

                url = settings.SUPABASE_URL.rstrip("/") + f"/auth/v1/admin/users/{user_id}"
                headers = {
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                }
                async with httpx.AsyncClient(timeout=20.0) as client:
                    r = await client.delete(url, headers=headers)
                    if r.status_code < 400:
                        auth_deleted = True
        except Exception as auth_error:
            # We'll still delete the profile row, but return a message indicating auth deletion failed
            print(f"Warning: Could not delete user from auth: {auth_error}")

        # Delete from users table
        db.table(settings.USERS_TABLE).delete().eq("id", user_id).execute()
        
        return {
            "message": (
                f"User {user_email} has been deleted successfully"
                if auth_deleted
                else f"User {user_email} deleted from users table; auth deletion may have failed"
            ),
            "deleted_user_id": user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )