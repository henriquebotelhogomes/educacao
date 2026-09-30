"""PostgreSQL transactions with explicit RLS request context."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from tutor_ai.platform.config import Settings


def psycopg_connection_url(settings: Settings) -> str:
    """Convert SQLAlchemy's driver-qualified URL to the psycopg connection format."""
    return str(settings.database_url).replace("postgresql+psycopg://", "postgresql://", 1)


@contextmanager
def database_transaction(
    settings: Settings,
    *,
    user_id: UUID | None = None,
    tenant_id: UUID | None = None,
    identity_bootstrap: bool = False,
    auth_lookup: bool = False,
) -> Iterator[psycopg.Connection[dict[str, object]]]:
    """Open a transaction and set RLS context only for its lifetime."""
    with psycopg.connect(psycopg_connection_url(settings), row_factory=dict_row) as connection:
        with connection.transaction():
            if user_id is not None:
                connection.execute(
                    "SELECT set_config('app.current_user_id', %s, true)",
                    (str(user_id),),
                )
            if tenant_id is not None:
                connection.execute(
                    "SELECT set_config('app.current_tenant_id', %s, true)",
                    (str(tenant_id),),
                )
            if identity_bootstrap:
                connection.execute("SELECT set_config('app.identity_bootstrap', 'true', true)")
            if auth_lookup:
                connection.execute("SELECT set_config('app.auth_lookup', 'true', true)")
            yield connection
