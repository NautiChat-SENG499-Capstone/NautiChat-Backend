from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from src.database import ConvBase


class Conversation(ConvBase):
    __tablename__ = "conversations"

    conversation_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(ConvBase):
    __tablename__ = "messages"

    message_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.conversation_id"), nullable=False)
    user_id: Mapped[int] = mapped_column(nullable=False)    

    input: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)

    conversation = relationship("Conversation", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", uselist=False, cascade="all, delete-orphan")


class Feedback(ConvBase):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.message_id"), unique=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, nullable=True)

    message = relationship("Message", back_populates="feedback")