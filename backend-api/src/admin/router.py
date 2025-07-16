from collections import defaultdict
from typing import Annotated

import hdbscan
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import schemas as auth_schemas
from src.auth.dependencies import get_admin_user
from src.auth.service import create_new_user, delete_user
from src.database import get_db_session
from src.llm import models as llm_models
from src.llm import schemas as llm_schemas

from . import service
from .schemas import (
    JSONUploadRequest,
    PDFUploadRequest,
    RawTextUploadRequest,
    UploadResponse,
)

router = APIRouter()


# TO DO:
# Could this be /users/create instead of /create?
@router.post("/create", status_code=201, response_model=auth_schemas.UserOut)
async def create_admin_user(
    _: Annotated[auth_schemas.UserOut, Depends(get_admin_user)],
    new_admin: auth_schemas.CreateUserRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> auth_schemas.UserOut:
    """Create new admin"""
    return await create_new_user(new_admin, db, is_admin=True)


@router.delete("/users/{id}", status_code=204)
async def delete_users(
    id: int,
    user: Annotated[auth_schemas.UserOut, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a user"""
    return await delete_user(id, user, db)


@router.get("/messages")
async def get_all_messages(
    _: Annotated[auth_schemas.UserOut, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[llm_schemas.Message]:
    """Get all messages"""
    # TODO: add pagination to this in case there are tons of messages

    result = await db.execute(
        select(llm_models.Message).order_by(llm_models.Message.message_id.desc())
    )
    return result.scalars().all()  # type: ignore


@router.get("/messages/clustered")
async def get_clustered_messages(
    _: Annotated[auth_schemas.UserOut, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, list[str]]:
    """Cluster all message inputs using HDBSCAN"""
    # fetch messages
    result = await db.execute(select(llm_models.Message))

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


@router.post("/documents/raw-data", status_code=201, response_model=UploadResponse)
async def upload_raw_text(
    current_admin: Annotated[auth_schemas.UserOut, Depends(get_admin_user)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    data: Annotated[RawTextUploadRequest, Depends(RawTextUploadRequest.as_form)],
) -> UploadResponse:
    """Upload a raw text blob to the vector DB and record metadata."""
    if not data.input_text:
        raise HTTPException(status_code=400, detail="Input text is required")

    await service.raw_text_upload_to_vdb(
        source=data.source,
        information=data.input_text,
        uploaded_by_id=current_admin.id,
        request=request,
        db=db,
    )

    return UploadResponse(detail="Raw text uploaded successfully")


@router.post("/documents/pdf", status_code=202, response_model=UploadResponse)
async def upload_pdf(
    current_admin: Annotated[auth_schemas.UserOut, Depends(get_admin_user)],
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    data: Annotated[PDFUploadRequest, Depends(PDFUploadRequest.as_form)],
) -> UploadResponse:
    """Upload a PDF to the vector DB and schedule background embedding/metadata logging."""
    # Note: I wasn't sure if we want to set source to the filename or a custom source, so I left it as a form field.
    if data.file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF uploads are supported.",
        )
    pdf_bytes = await data.file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    background_tasks.add_task(
        service.pdf_upload_to_vdb,
        source=data.source,
        filename=data.file.filename,
        pdf_bytes=pdf_bytes,
        uploaded_by_id=current_admin.id,
        db=db,
        request=request,
    )

    return UploadResponse(detail="PDF upload queued for processing.")


@router.post("/documents/json", status_code=201, response_model=UploadResponse)
async def json_data_upload(
    current_admin: Annotated[auth_schemas.UserOut, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
    data: Annotated[JSONUploadRequest, Depends(JSONUploadRequest.as_form)],
) -> UploadResponse:
    """
    Upload a JSON file to the vector DB and record metadata.
    """
    json_bytes = await data.file.read()
    if not json_bytes:
        raise HTTPException(status_code=400, detail="Uploaded JSON is empty.")

    await service.json_upload_to_vdb(
        source=data.source,
        json_bytes=json_bytes,
        uploaded_by_id=current_admin.id,
        request=request,
        db=db,
    )

    return UploadResponse(detail="JSON uploaded successfully")


@router.delete("/documents/{source}", status_code=204)
async def delete_document(
    source: str,
    current_admin: Annotated[auth_schemas.UserOut, Depends(get_admin_user)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Delete a document from both the vector DB and metadata store."""
    await service.source_remove_from_vdb(
        source_to_remove=source, request=request, db=db
    )
