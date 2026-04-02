import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client

from app import crud
from app.config import settings
from app.database.engine import get_db
from app.models.user import AppUser

_supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

_bearer = HTTPBearer()
_optional_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> AppUser:
    token = credentials.credentials
    try:
        response = _supabase.auth.get_user(token)
        auth_user = response.user
        if not auth_user:
            raise ValueError("No user returned")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = uuid.UUID(str(auth_user.id))
    email = auth_user.email or ""
    name = (auth_user.user_metadata or {}).get("full_name")

    return await crud.user.get_or_create(db, user_id, email, name)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> AppUser | None:
    if not credentials:
        return None
    token = credentials.credentials
    try:
        response = _supabase.auth.get_user(token)
        auth_user = response.user
        if not auth_user:
            return None
    except Exception:
        return None
    user_id = uuid.UUID(str(auth_user.id))
    email = auth_user.email or ""
    name = (auth_user.user_metadata or {}).get("full_name")
    return await crud.user.get_or_create(db, user_id, email, name)


async def require_admin(current_user: AppUser = Depends(get_current_user)) -> AppUser:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
