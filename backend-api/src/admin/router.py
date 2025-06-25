from typing import Annotated, List

from fastapi import APIRouter, Depends, Request

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sentence_transformers import SentenceTransformer
import hdbscan
import numpy as np
from collections import defaultdict
from pydantic import BaseModel

# Dependencies
from src.database import get_db_session
from src.auth.dependencies import get_admin_user

from src.auth.schemas import UserOut
from src.llm import models, schemas
from . import service

router = APIRouter()

class TextInput(BaseModel):
    source: str
    information: str

@router.get("/messages")
async def get_all_messages(
    _: Annotated[UserOut, Depends(get_admin_user)], db: Annotated[AsyncSession, Depends(get_db_session)]
) -> List[schemas.Message]:
    """Get all messages"""
    # TODO: add pagination to this in case there are tons of messages

    result = await db.execute(select(models.Message).order_by(models.Message.message_id.desc()))
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
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    embeddings = model.encode(inputs, convert_to_numpy=True, show_progress_bar=False)

    # cluster with hdbscan
    clusterer = hdbscan.HDBSCAN(min_cluster_size=3, min_samples=2, metric='euclidean')
    labels = clusterer.fit_predict(embeddings)

    # organize clusters into json and output
    clusters = defaultdict(list)
    for msg, label in zip(messages, labels):
        clusters[str(label)].append(msg.input)

    return dict(clusters)
    
@router.post("/data-upload", status_code=201)
async def raw_text_upload(
    input: TextInput,
    request: Request,
    _: Annotated[UserOut, Depends(get_admin_user)],
    
):
    """
    Endpoint for admins to submit raw text to be uploaded to vector database.
    """
    await service.raw_text_upload_to_vdb(input.source, input.information, request)

