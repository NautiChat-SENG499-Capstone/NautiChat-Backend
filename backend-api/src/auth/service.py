from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.settings import Settings
from src.auth.schemas import CreateUserRequest, Token
from src.auth import models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def get_user(username: str, db: Session) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def create_access_token(
    username: str,
    expires_delta: timedelta,
    settings: Settings,
) -> str:
    """Create a JWT access token for the given username with an expiration time."""
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": username, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def register_user(user_register: CreateUserRequest, settings: Settings, db: Session) -> Token:
    """Register a new user"""

    # check that the user does not already exist
    existing_user = get_user(user_register.username, db)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # create a new user
    new_user = models.User(
        username=user_register.username,
        onc_token=user_register.onc_token,
        hashed_password=get_password_hash(user_register.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(new_user.username, timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS), settings)
    return Token(access_token=token, token_type="bearer")


def get_user_by_token(token: str, settings: Settings, db: Session) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(username, db)
    if user is None:
        raise credentials_exception
    return user


def login_user(form_data: OAuth2PasswordRequestForm, settings: Settings, db: Session) -> Token:
    """Login and return a token"""
    invalid_credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # check that the user actually exists
    matched_user = get_user(form_data.username, db)
    if not matched_user:
        raise invalid_credentials_exception
    # check that the password is correct
    if not verify_password(form_data.password, matched_user.hashed_password):
        raise invalid_credentials_exception

    # create a new token
    token = create_access_token(
        matched_user.username,
        timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
        settings,
    )

    return Token(access_token=token, token_type="bearer")


def update_onc_token(user: models.User, new_onc_token: str, db: Session) -> models.User:
    """Update the ONC token for the given user"""

    user.onc_token = new_onc_token

    db.commit()
    db.refresh(user)

    return user
