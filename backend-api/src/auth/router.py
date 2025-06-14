from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.database import get_db
from src.settings import Settings

from . import models, schemas, service
from .dependencies import get_current_user, get_settings

router = APIRouter()


@router.post("/login")
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> schemas.Token:
    return service.login_user(form_data, settings, db)


@router.post("/register", status_code=201)
def register_user(
    user_request: schemas.CreateUserRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> schemas.Token:
    return service.register_user(user_request, settings, db)


@router.get("/me")
def get_me(user: Annotated[models.User, Depends(get_current_user)]) -> schemas.UserOut:
    """Get the current user"""
    # get_current_user is called automatically because of the Depends()
    return user


@router.put("/me/onc-token")
def update_onc_token(
    user: Annotated[models.User, Depends(get_current_user)],
    onc_token: str,
    db: Annotated[Session, Depends(get_db)],
) -> schemas.UserOut:
    """Update the ONC token for the current user"""
    return service.update_onc_token(user, onc_token, db)
