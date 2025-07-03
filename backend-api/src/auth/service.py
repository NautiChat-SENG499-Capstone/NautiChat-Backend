from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt  # JSON Web Token for creating and decoding tokens
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext  # For password hashing and verification
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User as UserModel
from src.auth.schemas import UpdateUserRequest, CreateUserRequest, ChangePasswordRequest, Token
from src.settings import Settings

# Create a password context using bycrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def create_access_token(
    username: str,
    expires_delta: timedelta,
    settings: Settings,
) -> str:
    """Create a JWT access token for the given username with an expiry time."""
    expire = datetime.now(timezone.utc) + expires_delta

    # Token payload (data stored in the token)
    to_encode = {"sub": username, "exp": expire}

    # Create and sign the JWT token with secret key and algorithm
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def get_user(username: str, db: AsyncSession) -> Optional[UserModel]:
    """Look up a user by their username in the DB"""
    user = select(UserModel).where(UserModel.username == username)
    result = await db.execute(user)
    return result.scalar_one_or_none()  # Fetch only single result


async def get_user_by_token(
    token: str, settings: Settings, db: AsyncSession
) -> UserModel:
    """Validates token (of user) before looking up user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Validate token of user
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    # Look up user
    user = await get_user(username, db)
    if user is None:
        raise credentials_exception

    return user


async def register_user(
    user_register: CreateUserRequest, settings: Settings, db: AsyncSession
) -> Token:
    """Register a new user and return a JWT token"""

    # Check if the username is already taken
    existing_user = await get_user(user_register.username, db)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # create a new user (with hashed password)
    new_user = UserModel(
        username=user_register.username,
        onc_token=user_register.onc_token,
        hashed_password=get_password_hash(user_register.password),
    )

    # Add new user to DB
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate and return a JWT token for the new user
    token = create_access_token(
        new_user.username, timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS), settings
    )
    return Token(access_token=token, token_type="bearer")


async def update_user_info(
    updated_user: UpdateUserRequest,
    user: UserModel,
    db: AsyncSession,        
) -> UserModel:
    """Update User Info for the Given User"""

    #Make sure that a field IS updated to avoid unnecessary db calls
    updated = False

    if updated_user.username and updated_user.username != user.username:
        existing_user = await get_user(updated_user.username, db)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )
        user.username = updated_user.username
        update = True

    if updated_user.onc_token:
        user.onc_token = updated_user.onc_token
        updated = True

    if updated:
        await db.commit()
        await db.refresh(user)

    return user


async def change_user_password(
    request: ChangePasswordRequest,
    user: UserModel,
    db: AsyncSession,
) -> UserModel:
    """Change user passward by first confirming current password"""
    # Check current password
    if not verify_password(request.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # If new password is empty
    if not request.new_password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="New password cannot be empty"
        )

    # Compare new password with confirmation password
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match"
        )
    
    # Check new password isn't the same as old one
    if verify_password(request.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password"
        )
    
    user.hashed_password = get_password_hash(request.new_password)
    await db.commit()
    await db.refresh(user)

    return user

async def login_user(
    form_data: OAuth2PasswordRequestForm, settings: Settings, db: AsyncSession
) -> Token:
    """Authenticate user credentials and return a JWT token"""
    # Check if user exists and that password is correct
    matched_user = await get_user(form_data.username, db)
    if not matched_user or not verify_password(
        form_data.password, matched_user.hashed_password
    ):
        # invalid credentials exception
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate and return a new token
    token = create_access_token(
        matched_user.username,
        timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
        settings,
    )
    return Token(access_token=token, token_type="bearer")


async def update_onc_token(
    user: UserModel, new_onc_token: str, db: AsyncSession
) -> UserModel:
    """Update the ONC token for the given user"""

    user.onc_token = new_onc_token

    # Update DB
    await db.commit()
    await db.refresh(user)

    return user
