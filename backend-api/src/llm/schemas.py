from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Feedback(BaseModel):
    rating: Annotated[int, Field(strict=True, ge=1, le=5)]
    comment: Optional[str] = None


class Message(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: int
    conversation_id: int
    user_id: int
    input: str
    response: str
    feedback: Optional[Feedback] = None


class Conversation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: int
    user_id: int
    title: Optional[str] = None
    messages: Optional[List[Message]] = []


class CreateConversationBody(BaseModel):
    title: Optional[str] = None


class CreateLLMQuery(BaseModel):
    input: str
    conversation_id: int