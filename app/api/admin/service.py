import asyncio

from fastapi import HTTPException, Request, status
from LLM.vector_db_upload import (
    prepare_embedding_input,
    prepare_embedding_input_from_preformatted,
    process_json,
    process_pdf,
    upload_to_vector_db,
)
from qdrant_client.http.models import FieldCondition, Filter, MatchValue, UpdateStatus
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.admin.models import VectorDocument
from src.logger import logger


def _upsert_metadata_stmt(source: str, uploaded_by_id: int) -> insert:
    """Prepare an upsert statement for VectorDocument metadata"""
    return (
        insert(VectorDocument)
        .values(
            source=source,
            usage_count=0,
            uploaded_by_id=uploaded_by_id,
        )
        .on_conflict_do_nothing(index_elements=["source"])
    )


async def _commit_upsert(db: AsyncSession, stmt) -> None:
    """Execute the upsert statement and commit the transaction"""
    try:
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


async def raw_text_upload_to_vdb(
    source: str,
    information: str,
    uploaded_by_id: int,
    request: Request,
    db: AsyncSession,
) -> None:
    """Format raw text, embed, upload to vector DB, and record metadata."""

    if not information.strip():
        raise HTTPException(status_code=400, detail="Input text is required")

    # Upsert metadata in your SQL table
    try:
        stmt = _upsert_metadata_stmt(source, uploaded_by_id)
        await _commit_upsert(db, stmt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Metadata upsert failed: {e}")
    # Format and embed the input text
    try:
        state = request.app.state
        prepared = prepare_embedding_input_from_preformatted(
            [{"paragraphs": [information], "page": [], "source": source}],
            state.rag.embedding,
        )
        await asyncio.to_thread(
            upload_to_vector_db, prepared, state.rag.qdrant_client_wrapper
        )
        logger.info(
            f"Raw text successfully uploaded for '{source}' by {uploaded_by_id}"
        )
    except Exception as e:
        logger.error(f"Raw text upload failed for '{source}' by {uploaded_by_id}: {e}")
        # attempt to rollback metadata to preserve consistency
        await db.execute(delete(VectorDocument).where(VectorDocument.source == source))
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Embedding/upload failed: {e}")


async def json_upload_to_vdb(
    source: str,
    json_bytes: bytes,
    uploaded_by_id: int,
    request: Request,
    db: AsyncSession,
) -> None:
    """Preprocess a JSON file, embed, and upload to vector DB, and upsert metadata."""

    if not json_bytes.strip():
        raise HTTPException(status_code=400, detail="Uploaded JSON is empty.")

    # Upsert metadata in your SQL table
    try:
        stmt = _upsert_metadata_stmt(source, uploaded_by_id)
        await _commit_upsert(db, stmt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Metadata upsert failed: {e}")
    # Preprocess and embed the JSON, upload to vector DB
    try:
        state = request.app.state

        processed_json = process_json(True, json_bytes, source=source)
        prepared_input = prepare_embedding_input(
            processed_json, embedding_model=state.rag.embedding
        )
        await asyncio.to_thread(
            upload_to_vector_db, prepared_input, state.rag.qdrant_client_wrapper
        )
        logger.info(f"JSON successfully uploaded for '{source}' by {uploaded_by_id}")
    except Exception as e:
        logger.error(f"JSON upload failed for '{source}' by {uploaded_by_id}: {e}")
        # attempt to rollback metadata to preserve consistency
        await db.execute(delete(VectorDocument).where(VectorDocument.source == source))
        await db.commit()
        raise HTTPException(
            status_code=502, detail=f"JSON embedding/upload failed: {e}"
        )


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

    if not pdf_bytes.strip():
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    # Upsert metadata in your SQL table
    try:
        stmt = _upsert_metadata_stmt(source, uploaded_by_id)
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metadata upsert failed: {e}",
        )

    # Preprocess & embed
    try:
        state = request.app.state
        processed = await asyncio.to_thread(process_pdf, True, pdf_bytes, source=source)
        if not processed:
            raise HTTPException(
                status_code=400, detail="No valid content found in PDF."
            )
        for page in processed:
            page["name"] = filename
        prepared = prepare_embedding_input(
            processed, embedding_model=state.rag.embedding
        )
        await asyncio.to_thread(
            upload_to_vector_db, prepared, state.rag.qdrant_client_wrapper
        )
        logger.info(f"PDF successfully uploaded for '{source}' by {uploaded_by_id}")
    except Exception as e:
        logger.error(f"PDF upload failed for '{source}' by {uploaded_by_id}: {e}")
        # attempt to rollback metadata to preserve consistency
        await db.execute(delete(VectorDocument).where(VectorDocument.source == source))
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"PDF embedding/upload failed: {e}",
        )


async def source_remove_from_vdb(
    source_to_remove: str, request: Request, db: AsyncSession
) -> None:
    """Delete points in vector DB and remove metadata record."""

    # Remove from vector DB
    try:
        state = request.app.state
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
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


async def get_all_documents(db: AsyncSession) -> list[VectorDocument]:
    """Return all vector documents from the database."""
    result = await db.execute(select(VectorDocument).order_by(VectorDocument.id))
    return result.scalars().all()


async def get_document_by_source(source: str, db: AsyncSession) -> VectorDocument:
    """Return a specific vector document by its source."""
    result = await db.execute(
        select(VectorDocument).where(VectorDocument.source == source)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=404, detail=f"No document found for source '{source}'"
        )
    return document


async def increment_usage(sources: list[str], db: AsyncSession) -> None:
    """Increment usage count for each source in the vector DB.
    Currently used in llm.service.generate_response to increment usage count for sources.
    Pre-existing sources in the VectorDB won't be in our database, so we can't increment usage for them.
    """
    if not sources:
        return
    try:
        # use single update statement for atomicity
        stmt = (
            update(VectorDocument)
            .where(VectorDocument.source.in_(sources))
            .values(usage_count=VectorDocument.usage_count + 1)
        )
        result = await db.execute(stmt)
        await db.commit()
        if result.rowcount == 0:
            logger.warning(
                f"No VectorDocument found for sources: {sources}. increment_usage could not increment usage."
            )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to increment usage: {e}")
