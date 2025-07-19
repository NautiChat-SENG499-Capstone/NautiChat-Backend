from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

# want to expose import for type checkers but don't want circular import
if TYPE_CHECKING:
    from src.admin.models import VectorDocument
    from src.llm.models import Conversation


class User(Base):
    """User Table in SQL DB"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    onc_token: Mapped[str] = mapped_column(String)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # one-to-many: a user can have many conversations
    # Ensures deleting a user also deletes all their conversations
    conversations: Mapped[List["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    # one-to-many: a user can upload many vector documents
    # Ensures deleting a user doesnt delete vector documents
    # but sets their uploaded_by_id to None
    vector_documents: Mapped[List["VectorDocument"]] = relationship(
        back_populates="uploaded_by",
        passive_deletes=True,
    )
