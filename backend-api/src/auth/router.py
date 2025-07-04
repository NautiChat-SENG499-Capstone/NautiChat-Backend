from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session
from src.middleware import limiter
from src.settings import Settings, get_settings

from . import service
from .dependencies import get_current_user
from .models import User
from .schemas import UpdateUserRequest, CreateUserRequest, ChangePasswordRequest, Token, UserOut

router = APIRouter()


@router.post("/login", response_model=Token)
@limiter.limit("6/minute")
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Token:
    """Authenticate user trying to login"""
    return await service.login_user(form_data, settings, db)


@router.post("/register", status_code=201, response_model=Token)
async def register_user(
    user_request: CreateUserRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Token:
    """Register a new user"""
    return await service.register_user(user_request, settings, db)


@router.get("/me")
async def get_me(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserOut:
    """Get the current user"""
    # Uses get_current_user() dependency to grab user
    return user


@router.put("/me", response_model=UserOut)
async def update_user_info(
    updated_user: UpdateUserRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserOut:
    """Update current user's profile info"""
    return await service.update_user_info(updated_user, user, db)


@router.put("/me/password", response_model=UserOut)
async def change_password(
    request: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserOut:
    """Change the password for the user"""
    return await service.change_user_password(request, user, db)


@router.put("/me/onc-token", response_model=UserOut)
async def update_onc_token(
    user: Annotated[User, Depends(get_current_user)],
    onc_token: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserOut:
    """Update the ONC token for the current user"""
    return await service.update_onc_token(user, onc_token, db)
