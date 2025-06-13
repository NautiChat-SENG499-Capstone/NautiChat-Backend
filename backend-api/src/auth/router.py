from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

# Dependencies
from src.database import get_db_session
from .dependencies import get_current_user, get_settings

from .models import User
from .schemas import Token, CreateUserRequest, UserOut
from . import config, service

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[config.Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Token:
    return await service.login_user(form_data, settings, db)


@router.post("/register", status_code=201, response_model=Token)
async def register_user(
    user_request: CreateUserRequest,
    settings: Annotated[config.Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Token:
    return await service.register_user(user_request, settings, db)


@router.get("/me")
async def get_me(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    """Get the current user"""
    # get_current_user is called automatically because of the Depends()
    return user


@router.put("/me/onc-token", response_model=UserOut)
async def update_onc_token(
    user: Annotated[User, Depends(get_current_user)],
    onc_token: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserOut:
    """Update the ONC token for the current user"""
    return await service.update_onc_token(user, onc_token, db)
