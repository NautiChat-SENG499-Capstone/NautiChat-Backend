from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.auth.models import User
from src.database import Base


class VectorDocument(Base):
    """Vector Document Table in SQL DB"""

    __tablename__ = "vector_documents"
    __table_args__ = (UniqueConstraint("source", name="uq_vector_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    uploaded_by: Mapped["User"] = relationship(
        "User",
        back_populates="vector_documents",
        passive_deletes=True,
    )
