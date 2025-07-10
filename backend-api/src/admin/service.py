from fastapi import HTTPException, Request
from qdrant_client.http.models import FieldCondition, Filter, MatchValue, UpdateStatus
from sqlalchemy.ext.asyncio import AsyncSession

from LLM.vectorDBUpload import (
    prepare_embedding_input,
    prepare_embedding_input_from_preformatted,
    process_pdf,
    upload_to_vector_db,
)


async def raw_text_upload_to_vdb(
    source: str, information: str, request: Request
) -> None:
    """Format raw text input, embed, and upload to vector db"""
    # Create a new DB object with the text
    state = request.app.state
    if not state.llm or not state.rag:
        raise HTTPException(status_code=500, detail="LLM/RAG not initialized")

    input_raw_text = [{"paragraphs": [information], "page": [], "source": source}]
    upload_to_vector_db(
        prepare_embedding_input_from_preformatted(input_raw_text, state.rag.embedding),
        state.rag.qdrant_client_wrapper,
    )
    # Need an upload to standard db of source


async def pdf_upload_to_vdb(source: str, pdf_bytes: bytes, request: Request) -> None:
    """Preprocess a pdf file, embed, and upload to vector db"""
    # Create a new DB object with the text
    state = request.app.state
    if not state.llm or not state.rag:
        raise HTTPException(status_code=500, detail="LLM/RAG not initialized")

    processed_pdf = process_pdf(True, pdf_bytes, source=source)
    prepared_input = prepare_embedding_input(
        processed_pdf, embedding_model=state.rag.embedding
    )

    upload_to_vector_db(prepared_input, state.rag.qdrant_client_wrapper)
    # Need an upload to standard db of source


async def source_remove_from_vdb(source_to_remove: str, request: Request) -> None:
    """Filter vector db for points with provided source and remove them"""

    state = request.app.state
    if not state.llm or not state.rag:
        raise HTTPException(status_code=500, detail="LLM/RAG not initialized")

    # Define a filter on the "source" field in the payload
    filter_condition = Filter(
        must=[FieldCondition(key="source", match=MatchValue(value=source_to_remove))]
    )

    # Delete matching points from the collection
    result = state.rag.qdrant_client.delete(
        state.rag.collection_name, points_selector=filter_condition
    )

    if result.status != UpdateStatus.COMPLETED:
        raise HTTPException(
            status_code=500, detail="Deletion from vector database failed"
        )

    # Need a remove from standard db of source
