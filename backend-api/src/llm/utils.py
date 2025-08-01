from enum import Enum
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from LLM.core import LLM
from src.llm.models import Conversation, Message
from src.logger import logger


# Pydantic models for better autocomplete within this file. Could be nice for AI LLM code to also use pydantic models
class Role(str, Enum):
    user = "user"
    system = "system"


class MessageContext(BaseModel):
    role: Role
    content: str


def get_llm(app: FastAPI) -> LLM:
    if getattr(app.state, "llm", None) is None:
        logger.info("Initializing LLM (this may take a while)...")
        try:
            app.state.llm = LLM(app.state.env)
            logger.info("LLM instance initialized successfully.")
        except Exception as e:
            logger.error(f"LLM initialization failed: {e}")
            raise RuntimeError(f"LLM initialization failed: {e}")

        logger.info("Getting RAG instance ...")
        app.state.rag = app.state.llm.RAG_instance
        logger.info("RAG instance initialized successfully.")
    return app.state.llm


async def get_context(
    conversation_id: int, max_words: int, db: AsyncSession
) -> List[dict]:
    """Return a list of messages for the LLM to use as context"""

    conversation_result = await db.execute(
        select(Conversation).filter(Conversation.conversation_id == conversation_id)
    )
    conversation = conversation_result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # most recent messages first
    messages: List[Message] = conversation.messages[::-1]
    context: List[MessageContext] = []

    context_words = 0

    for message in messages:
        message_words = (
            4 + len(message.input.split()) + len(message.response.split())
        )  # extra words for "role", "content"
        if context_words + message_words < max_words:
            context.append(MessageContext(role=Role.user, content=message.input))
            context.append(MessageContext(role=Role.system, content=message.response))
            context_words += message_words
        else:
            break

    return [model.model_dump(mode="json") for model in context]
