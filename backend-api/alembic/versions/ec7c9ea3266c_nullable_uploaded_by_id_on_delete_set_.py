"""nullable uploaded_by_id + ON DELETE SET NULL

Revision ID: ec7c9ea3266c
Revises: 52726b3af26e
Create Date: 2025-07-15 11:34:46.724532

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ec7c9ea3266c"
down_revision: Union[str, Sequence[str], None] = "52726b3af26e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "vector_documents", sa.Column("uploaded_by_id", sa.Integer(), nullable=True)
    )
    op.create_index(
        op.f("ix_vector_documents_uploaded_by_id"),
        "vector_documents",
        ["uploaded_by_id"],
        unique=False,
    )
    op.create_foreign_key(
        None,
        "vector_documents",
        "users",
        ["uploaded_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_column("vector_documents", "created_at")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "vector_documents",
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.drop_constraint(None, "vector_documents", type_="foreignkey")
    op.drop_index(
        op.f("ix_vector_documents_uploaded_by_id"), table_name="vector_documents"
    )
    op.drop_column("vector_documents", "uploaded_by_id")
    # ### end Alembic commands ###
