from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from .dependencies import get_current_user
from .schemas import CreateUserRequest, Token, User

router = APIRouter()


@router.post("/login")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """Login and return a token"""
    # Validate the user and return a token
    # For now just return a fake token every time
    return Token(access_token=form_data.username, token_type="bearer")


@router.post("/register")
def register_user(user: CreateUserRequest) -> Token:
    """Register a new user"""
    # Save the user to the database
    # Do nothing right now because we allow all logins anyways
    return Token(access_token=user.username, token_type="bearer")


@router.get("/me")
def get_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Get the current user"""
    # get_current_user is called automatically because of the Depends()
    return user
