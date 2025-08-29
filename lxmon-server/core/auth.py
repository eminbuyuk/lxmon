"""
Authentication module for JWT tokens and API key validation.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
import logging

from core.config import settings
from core.database import get_db
from models.models import User

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT security
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

# JWT Configuration
SECRET_KEY = getattr(settings, 'SECRET_KEY', "your-secret-key-here")
ALGORITHM = getattr(settings, 'ALGORITHM', "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = getattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30)

def verify_api_key(api_key: str) -> bool:
    """Verify agent API key."""
    return api_key in settings.AGENT_API_KEYS

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    # Get user from database
    result = await db.execute(
        select(User).where(User.username == username, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user

def get_current_tenant_id(user: User = Depends(get_current_user)) -> str:
    """Get current tenant ID from authenticated user."""
    return user.tenant_id

def get_agent_tenant_id(api_key: str) -> str:
    """Get tenant ID for agent based on API key."""
    # For now, use default tenant. In production, you might have a mapping
    return settings.DEFAULT_TENANT_ID
