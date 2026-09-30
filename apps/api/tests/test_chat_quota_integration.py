"""Tutor quota integration tests against the local PostgreSQL instance."""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import PostgresDsn, SecretStr
from test_identity_integration import (
    ADMIN_DATABASE_URL,
    TEST_DATABASE_URL,
    InMemorySessionStore,
    csrf_headers,
    signup,
)
from tutor_ai.ai.tutor import TutorEvent
from tutor_ai.main import create_app
from tutor_ai.platform.config import Settings
from tutor_ai.platform.database import database_transaction


class FallbackTutor:
    async def stream(self, *_: object) -> AsyncIterator[TutorEvent]:
        yield TutorEvent(
            "fallback",
            {"reason": "no_evidence", "message": "Sem evidência suficiente."},
        )


@pytest.fixture(autouse=True)
def clear_chat_tables() -> Generator[None, None, None]:
    with psycopg.connect(ADMIN_DATABASE_URL) as connection:
        connection.execute('TRUNCATE TABLE audit_log, membership, tenant, "user" CASCADE')
        connection.commit()
    yield
    with psycopg.connect(ADMIN_DATABASE_URL) as connection:
        connection.execute('TRUNCATE TABLE audit_log, membership, tenant, "user" CASCADE')
        connection.commit()


def test_tutor_rejects_questions_after_monthly_quota_is_reserved() -> None:
    limited_settings = Settings(
        database_url=PostgresDsn(
            TEST_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
        ),
        environment="test",
        jwt_secret=SecretStr("test-secret-not-for-production-with-at-least-32-bytes"),
        minio_access_key="minioadmin",
        minio_secret_key=SecretStr("minioadmin_dev_only"),
        cookie_secure=False,
        readiness_check_dependencies=False,
        telemetry_enabled=False,
        free_tutor_questions_per_month=1,
    )
    app = create_app(limited_settings)
    app.state.session_store = InMemorySessionStore({})
    app.state.tutor_service = FallbackTutor()

    with TestClient(app) as client:
        session = signup(client, "quota@example.com", "Quota")
        tenant_id = UUID(session["tenant_id"])
        user_id = UUID(session["user_id"])
        knowledge_base_id = uuid4()
        with database_transaction(
            limited_settings,
            user_id=user_id,
            tenant_id=tenant_id,
        ) as connection:
            connection.execute(
                """
                INSERT INTO knowledge_base (id, tenant_id, name, is_default)
                VALUES (%s, %s, 'Base pessoal', true)
                """,
                (knowledge_base_id, tenant_id),
            )

        thread_response = client.post(
            "/api/v1/chat/threads",
            headers=csrf_headers(client),
            json={"title": "Cota"},
        )
        assert thread_response.status_code == 201
        thread_id = thread_response.json()["id"]

        first = client.post(
            f"/api/v1/chat/threads/{thread_id}/messages",
            headers=csrf_headers(client),
            json={"content": "Primeira pergunta"},
        )
        second = client.post(
            f"/api/v1/chat/threads/{thread_id}/messages",
            headers=csrf_headers(client),
            json={"content": "Segunda pergunta"},
        )

        assert first.status_code == 200
        assert second.status_code == 403
        assert second.json()["code"] == "plan_limit_reached"

        with database_transaction(
            limited_settings,
            user_id=user_id,
            tenant_id=tenant_id,
        ) as connection:
            usage_count = connection.execute(
                """
                SELECT count(*) AS count
                FROM usage_event
                WHERE event_type = 'tutor_question'
                """
            ).fetchone()
        assert usage_count is not None
        assert usage_count["count"] == 1
