from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field

from LLM.schemas import ObtainedParamsDictionary


class Feedback(BaseModel):
    """User Feedback on LLM Response"""

    rating: Annotated[int, Field(strict=True, ge=1, le=5)]
    comment: Optional[str] = None


class Message(BaseModel):
    """Single Interaction between user and LLM"""

    # Allows model to be populated from SQLAlchemy ORM objects
    model_config = ConfigDict(from_attributes=True)

    message_id: int
    conversation_id: int
    user_id: int
    input: str
    response: str
    request_id: Optional[int] = None
    feedback: Optional[Feedback] = None
    citation: Optional[str] = None
    sources: Optional[list[str]] = Field(default_factory=list)
    onc_api_url: Optional[str] = None


class Conversation(BaseModel):
    """Conversation Thread b/w user and LLM"""

    model_config = ConfigDict(from_attributes=True)

    conversation_id: int
    user_id: int
    title: Optional[str] = None
    messages: Optional[list[Message]] = Field(default_factory=list)
    obtained_params: ObtainedParamsDictionary = Field(
        default_factory=ObtainedParamsDictionary
    )


class CreateConversationBody(BaseModel):
    """Payload for creating new conversation"""

    title: Optional[str] = None


class CreateLLMQuery(BaseModel):
    """Payload sent when querying LLM"""

    input: str
    conversation_id: int
