from functools import lru_cache
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.database import get_db

from . import config, service, models

oauth2_scheme_required = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@lru_cache
def get_settings() -> config.Settings:
    # pylance doesn't understand that the Settings fields are loaded at runtime from the .env file,
    # so use type: ignore to suppress the editor error
    return config.Settings()  # type: ignore[call-arg]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme_required)],
    settings: Annotated[config.Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> models.User:
    return service.get_user_by_token(token, settings, db)


def get_optional_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme_optional)],
    settings: Annotated[config.Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> Optional[models.User]:
    """Dependency to get the current user if they are authenticated, or None if not."""
    if token is None:
        return None
    return service.get_user_by_token(token, settings, db)


def get_admin_user(
    current_user: Annotated[models.User, Depends(get_current_user)],
) -> models.User:
    """Dependency to ensure the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )
    return current_user
