from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

# Dependencies (outside of auth module)
from src.database import get_db_session
from src.settings import Settings, get_settings

from . import service, models

# Helpers from FastAPI security to extract OAuth2 token from HTTP request
oauth2_scheme_required = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme_required)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> models.User:
    """Retrieves and validates a user by token"""
    return await service.get_user_by_token(token, settings, db)


async def get_optional_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme_optional)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Optional[models.User]:
    """Dependency to get the current user if they are authenticated"""
    if token is None:
        return None
    return await service.get_user_by_token(token, settings, db)


async def get_admin_user(
    current_user: Annotated[models.User, Depends(get_current_user)],
) -> models.User:
    """Dependency to ensure the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )
    return current_user
