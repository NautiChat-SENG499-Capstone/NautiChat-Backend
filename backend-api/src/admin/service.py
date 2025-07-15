import uuid

from fastapi import HTTPException, Request, status
from qdrant_client.http.models import FieldCondition, Filter, MatchValue, UpdateStatus
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from LLM.vectorDBUpload import (
    prepare_embedding_input,
    prepare_embedding_input_from_preformatted,
    process_pdf,
    upload_to_vector_db,
)
from src.admin.models import VectorDocument


def _upsert_metadata_stmt(source: str, uploaded_by_id: int) -> insert:
    """Prepare an upsert statement for VectorDocument metadata"""
    return (
        insert(VectorDocument)
        .values(
            source=source,
            usage_count=0,
            uploaded_by_id=uploaded_by_id,
        )
        .on_conflict_do_nothing(index_elements=[VectorDocument.source])
    )


async def _commit_upsert(db: AsyncSession, stmt) -> None:
    """Execute the upsert statement and commit the transaction"""
    try:
        await db.execute(stmt)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")


async def _upload_to_vector_db(state, prepared):
    """Upload data to the vector database"""
    try:
        upload_to_vector_db(prepared, state.rag.qdrant_client_wrapper)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vector DB upload failed: {exc}")


async def raw_text_upload_to_vdb(
    source: str,
    information: str,
    uploaded_by_id: int,
    request: Request,
    db: AsyncSession,
) -> None:
    """Format raw text, embed, upload to vector DB, and record metadata."""
    if not source:
        source = f"{uuid.uuid4().hex[:8]}"
    if not information:
        raise HTTPException(status_code=400, detail="information is required")

    state = request.app.state
    if not state.llm or not state.rag:
        raise HTTPException(status_code=500, detail="LLM/RAG not initialized")

    prepared = prepare_embedding_input_from_preformatted(
        [{"paragraphs": [information], "page": [], "source": source}],
        state.rag.embedding,
    )
    await _upload_to_vector_db(state, prepared)

    stmt = _upsert_metadata_stmt(source, uploaded_by_id)
    await _commit_upsert(db, stmt)


async def pdf_upload_to_vdb(
    *,
    source: str,
    filename: str,
    pdf_bytes: bytes,
    uploaded_by_id: int,
    request: Request,
    db: AsyncSession,
) -> None:
    """
    Background task: preprocess PDF, embed, upload to vector DB,
    then upsert metadata (source, uploader).
    """
    # Preprocess & embed
    try:
        state = request.app.state
        if not state.llm or not state.rag:
            raise HTTPException(status_code=500, detail="LLM/RAG not initialized")
        processed = process_pdf(True, pdf_bytes, source=source)
        for page in processed:
            page["name"] = filename
        prepared = prepare_embedding_input(
            processed, embedding_model=state.rag.embedding
        )
        upload_to_vector_db(prepared, state.rag.qdrant_client_wrapper)
    except Exception:
        raise

    # Upsert metadata in your SQL table
    stmt = _upsert_metadata_stmt(source, uploaded_by_id)
    try:
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metadata upsert failed: {e}",
        )


async def source_remove_from_vdb(
    source_to_remove: str, request: Request, db: AsyncSession
) -> None:
    """Delete points in vector DB and remove metadata record."""
    if not source_to_remove:
        raise HTTPException(status_code=400, detail="source_to_remove is required")

    state = request.app.state
    if not state.llm or not state.rag:
        raise HTTPException(status_code=500, detail="LLM/RAG not initialized")

    # Remove from vector DB
    try:
        filter_cond = Filter(
            must=[
                FieldCondition(key="source", match=MatchValue(value=source_to_remove))
            ]
        )
        result = state.rag.qdrant_client.delete(
            state.rag.collection_name, points_selector=filter_cond
        )
        if result.status != UpdateStatus.COMPLETED:
            raise HTTPException(status_code=502, detail="Vector DB deletion incomplete")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vector DB deletion failed: {exc}")

    # Remove metadata in SQL DB
    try:
        del_stmt = delete(VectorDocument).where(
            VectorDocument.source == source_to_remove
        )
        await db.execute(del_stmt)
        await db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")
