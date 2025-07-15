from collections import defaultdict
from typing import Annotated, List

import hdbscan
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
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

from . import service

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


@router.post(
    "/documents/raw-data",
    status_code=status.HTTP_201_CREATED,
)
async def raw_text_upload(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[UserOut, Depends(get_admin_user)],
    source: str = Form(...),
    input_text: str = Form(...),
) -> dict:
    """
    Upload a raw text blob to the vector DB and record metadata.
    filename can be a user supplied identifier or will be auto-generated.
    """
    if not input_text:
        raise HTTPException(status_code=400, detail="Input text is required")
    await service.raw_text_upload_to_vdb(
        source=source,
        information=input_text,
        uploaded_by_id=current_admin.id,
        request=request,
        db=db,
    )
    return {"detail": "Raw text uploaded successfully"}


@router.post(
    "/documents/pdf",
    status_code=status.HTTP_202_ACCEPTED,
)
async def pdf_data_upload(
    *,
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    source: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
    current_admin: UserOut = Depends(get_admin_user),
):
    """Upload a PDF file to the vector DB and record metadata.
    The PDF will be processed in the background."""
    # validate and process the uploaded PDF file
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF uploads are supported.",
        )
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded PDF is empty.",
        )

    # schedule the background job
    background_tasks.add_task(
        service.pdf_upload_to_vdb,
        source=source,
        filename=file.filename,
        pdf_bytes=pdf_bytes,
        uploaded_by_id=current_admin.id,
        db=db,
        request=request,
    )

    # Return immediately
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"detail": "PDF upload queued for processing."},
    )


@router.delete(
    "/documents/{source}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def source_remove(
    source: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[UserOut, Depends(get_admin_user)],
) -> None:
    """
    Delete source in the vector DB and corresponding metadata for a source.
    """
    await service.source_remove_from_vdb(
        source_to_remove=source,
        request=request,
        db=db,
    )
