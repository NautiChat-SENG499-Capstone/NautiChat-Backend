from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from LLM.vectorDBUpload import prepare_embedding_input_from_preformatted, upload_to_vector_db

async def raw_text_upload_to_vdb(
    source: str, 
    information: str, 
    request: Request
    ) -> None:
    """Format raw text input, embed, and upload to vector db"""
    # Create a new DB object with the text
    state = request.app.state
    if not state.llm or not state.rag:
        raise HTTPException(status_code=500, detail="LLM/RAG not initialized")
    
    input_raw_text = [{'paragraphs': [information], 'page': [], 'source': source}]
    upload_to_vector_db(prepare_embedding_input_from_preformatted(input_raw_text, state.rag.embedding), state.rag.qdrant_client_wrapper)
        
