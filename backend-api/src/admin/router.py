from collections import defaultdict
from typing import Annotated, List

import hdbscan
from fastapi import APIRouter, Depends
from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import models as auth_models
from src.auth import schemas as auth_schemas
from src.auth.dependencies import get_admin_user
from src.auth.schemas import UserOut
from src.auth.service import create_new_user, delete_user
from src.database import get_db_session
from src.llm import models, schemas

router = APIRouter()


@router.post("/create", status_code=201, response_model=UserOut)
async def create_admin_user(
    _: Annotated[auth_models.User, Depends(get_admin_user)],
    new_admin: auth_schemas.CreateUserRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserOut:
    """Create new admin"""
    return await create_new_user(new_admin, db, is_admin=True)


@router.delete("/users/{id}", status_code=204)
async def delete_users(
    id: int,
    user: Annotated[auth_models.User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Delete a user"""
    return await delete_user(id, user, db)


@router.get("/messages")
async def get_all_messages(
    _: Annotated[UserOut, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> List[schemas.Message]:
    """Get all messages"""
    # TODO: add pagination to this in case there are tons of messages

    result = await db.execute(
        select(models.Message).order_by(models.Message.message_id.desc())
    )
    return result.scalars().all()  # type: ignore


@router.get("/messages/clustered")
async def get_clustered_messages(
    _: Annotated[UserOut, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Cluster all message inputs using HDBSCAN"""
    # fetch messages
    result = await db.execute(select(models.Message))

    messages = result.scalars().all()

    if not messages:
        return {}

    inputs = [m.input for m in messages]

    # embed inputs
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embeddings = model.encode(inputs, convert_to_numpy=True, show_progress_bar=False)

    # cluster with hdbscan
    clusterer = hdbscan.HDBSCAN(min_cluster_size=3, min_samples=2, metric="euclidean")
    labels = clusterer.fit_predict(embeddings)

    # organize clusters into json and output
    clusters = defaultdict(list)
    for msg, label in zip(messages, labels):
        clusters[str(label)].append(msg.input)

    return dict(clusters)
