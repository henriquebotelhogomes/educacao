"""Persistence operations for tutor usage."""

from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

from psycopg import Connection


def reserve_monthly_question(
    connection: Connection[dict[str, object]],
    *,
    tenant_id: UUID,
    user_id: UUID,
    limit: int,
) -> bool:
    """Atomically reserve one tutor question within the tenant's monthly allowance."""
    connection.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
        (str(tenant_id),),
    )
    row = connection.execute(
        """
        SELECT count(*) AS count
        FROM usage_event
        WHERE event_type = 'tutor_question'
          AND created_at >= date_trunc('month', CURRENT_TIMESTAMP)
        """
    ).fetchone()
    if row is None or cast(int, row["count"]) >= limit:
        return False
    connection.execute(
        """
        INSERT INTO usage_event (id, tenant_id, user_id, event_type)
        VALUES (%s, %s, %s, 'tutor_question')
        """,
        (uuid4(), tenant_id, user_id),
    )
    return True
