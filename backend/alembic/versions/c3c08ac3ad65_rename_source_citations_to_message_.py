"""Rename source_citations to message_citations.

Revision ID: c3c08ac3ad65
Revises: 732b71fe5b4a
Create Date: 2026-09-22 06:19:10.884549
"""
from collections.abc import Sequence

from alembic import op

revision: str = "c3c08ac3ad65"
down_revision: str | Sequence[str] | None = "732b71fe5b4a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("source_citations", "message_citations")
    op.execute(
        "ALTER INDEX ix_source_citations_chunk_id "
        "RENAME TO ix_message_citations_chunk_id"
    )
    op.execute(
        "ALTER INDEX ix_source_citations_message_id "
        "RENAME TO ix_message_citations_message_id"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX ix_message_citations_chunk_id "
        "RENAME TO ix_source_citations_chunk_id"
    )
    op.execute(
        "ALTER INDEX ix_message_citations_message_id "
        "RENAME TO ix_source_citations_message_id"
    )
    op.rename_table("message_citations", "source_citations")
