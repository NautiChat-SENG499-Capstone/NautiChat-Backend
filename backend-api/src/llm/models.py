from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Integer, String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from src.database import Base

# want to expose import for type checkers but don't want circular import
if TYPE_CHECKING:
    from src.auth.models import User


class Conversation(Base):
    """Conversation Table in SQL DB"""
    __tablename__ = "conversations"

    conversation_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # one-to-many: conversation can have many messages
    # Delete messages if conversation is deleted
    # NOTE: lazy:selectin eager loads by default
    messages: Mapped[List["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan", lazy="selectin")
    # Many-to-one: links to user who 'owns' conversation
    user: Mapped["User"] = relationship(back_populates="conversations")


class Message(Base):
    """Message Table in SQL DB"""
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("LENGTH(input) >= 5 AND LENGTH(input) <= 1000", name="ck_message_input_length"),
    )

    message_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.conversation_id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    input: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)

    #many-to-one: each message belongs to a conversation
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    #one-to-one: one message, one feedback
    # NOTE: lazy:selectin eager loads by default
    feedback: Mapped["Feedback"] = relationship(back_populates="message", uselist=False, cascade="all, delete-orphan", lazy="selectin")

    @validates('input')
    def validate_input(self, key, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Message input cannot be empty or whitespace")
        if len(trimmed) < 5:
            raise ValueError("Input must be at least 5 characters long")
        if len(trimmed) > 1000:
            raise ValueError("Input exceeds maximum length of 1000 characters")
        return trimmed

    @validates('response')
    def validate_response(self, key, value: str) -> str:
        if value is None:
            raise ValueError("LLM response cannot be None")
        return value


class Feedback(Base):
    """Feedback Table in SQL DB"""
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.message_id"), unique=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, nullable=True)

    message: Mapped["Message"] = relationship(back_populates="feedback")
