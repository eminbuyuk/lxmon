"""
Authentication router for dashboard users.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from core.database import get_db
from core.auth import (
    verify_password, create_access_token, get_password_hash,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from models.models import User
from core.schemas import UserCreate, UserResponse, Token

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/login", response_model=Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT access token.

    **Credentials:**
    - **username**: User's username
    - **password**: User's password

    **Returns:**
    - **access_token**: JWT token for API authentication
    - **token_type**: "bearer"

    **Usage:**
    Include the token in Authorization header: `Bearer <access_token>`
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse, tags=["Authentication"])
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.

    **Required Fields:**
    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Password (minimum 8 characters)

    **Optional Fields:**
    - **tenant_id**: Organization/tenant identifier (defaults to "default")
    """
    # Check if user already exists
    result = await db.execute(
        select(User).where(
            (User.username == user_data.username) | (User.email == user_data.email)
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        tenant_id=user_data.tenant_id or "default"
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"New user registered: {new_user.username}")
    return UserResponse.from_orm(new_user)

@router.get("/me", response_model=UserResponse, tags=["Authentication"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    **Returns:** Current user's profile information including:
    - User ID, username, email
    - Account status and tenant information
    - Creation and last login timestamps
    """
    return UserResponse.from_orm(current_user)

@router.post("/refresh-token", response_model=Token, tags=["Authentication"])
async def refresh_access_token(current_user: User = Depends(get_current_user)):
    """
    Refresh the current user's access token.

    **Returns:** New JWT access token with extended expiration time.
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )

    logger.info(f"Token refreshed for user: {current_user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/change-password", tags=["Authentication"])
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change the current user's password.

    **Required:**
    - **old_password**: Current password for verification
    - **new_password**: New password (minimum 8 characters)

    **Security Notes:**
    - Old password is required for verification
    - New password must meet security requirements
    - All active sessions remain valid until token expiration
    """
    # Verify old password
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Validate new password strength
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )

    # Update password
    current_user.hashed_password = get_password_hash(new_password)
    await db.commit()

    logger.info(f"Password changed for user: {current_user.username}")
    return {"message": "Password changed successfully"}
