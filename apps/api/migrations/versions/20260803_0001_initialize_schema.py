"""Initialize the Alembic migration history without domain tables."""

from collections.abc import Sequence

revision: str = "20260803_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Reserve the initial revision for Marco 1 domain tables."""


def downgrade() -> None:
    """Keep Marco 0 schema-free."""
