from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.models import User
from src.auth.schemas import CreateUserRequest, UserOut
from src.auth.service import get_password_hash, get_user
from src.logger import logger


async def create_user(
    user_request: CreateUserRequest,
    db: AsyncSession,
    is_admin: bool = False,
) -> User:
    existing_user = await get_user(user_request.username, db)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    new_user = User(
        username=user_request.username,
        hashed_password=get_password_hash(user_request.password),
        onc_token=user_request.onc_token,
        is_admin=is_admin,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
