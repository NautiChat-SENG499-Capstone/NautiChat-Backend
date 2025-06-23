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
        CheckConstraint("LENGTH(input) >= 1 AND LENGTH(input) <= 1000", name="ck_message_input_length"),
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


class Feedback(Base):
    """Feedback Table in SQL DB"""
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.message_id"), unique=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, nullable=True)

    message: Mapped["Message"] = relationship(back_populates="feedback")
