"""Resize the P&M RAG vectors for the local multilingual E5 model.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
"""
from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "c8d9e0f1a2b3"
down_revision: str | Sequence[str] | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _require_empty_table() -> None:
    connection = op.get_bind()
    count = connection.execute(
        sa.text("SELECT COUNT(*) FROM rag_documents")
    ).scalar_one()
    if count:
        raise RuntimeError(
            "Cannot resize rag_documents.embedding while embedded chunks exist. "
            "Re-embed the knowledge base before applying this migration."
        )


def upgrade() -> None:
    _require_empty_table()
    op.alter_column(
        "rag_documents",
        "embedding",
        existing_type=pgvector.sqlalchemy.Vector(dim=768),
        type_=pgvector.sqlalchemy.Vector(dim=384),
        existing_nullable=False,
    )


def downgrade() -> None:
    _require_empty_table()
    op.alter_column(
        "rag_documents",
        "embedding",
        existing_type=pgvector.sqlalchemy.Vector(dim=384),
        type_=pgvector.sqlalchemy.Vector(dim=768),
        existing_nullable=False,
    )
