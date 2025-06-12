from typing import Annotated, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Dependencies
from src.database import get_db_session
from src.auth.dependencies import get_admin_user

from src.auth.schemas import UserOut
from src.llm import models, schemas

router = APIRouter()


@router.get("/messages")
async def get_all_messages(
    _: Annotated[UserOut, Depends(get_admin_user)], 
    db: Annotated[AsyncSession, Depends(get_db_session)]
) -> List[schemas.Message]:
    """Get all messages"""
    # TODO: add pagination to this in case there are tons of messages
    
    result = await db.execute(
        select(models.Message).order_by(models.Message.message_id.desc())
    )
    return result.scalars().all()  # type: ignore
