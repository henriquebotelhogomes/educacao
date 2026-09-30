"""Document admission tests with real PostgreSQL and deterministic object storage."""

from __future__ import annotations

import secrets
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import PostgresDsn, SecretStr
from tutor_ai.identity.domain import Role
from tutor_ai.identity.sessions import BrowserSession
from tutor_ai.main import create_app
from tutor_ai.platform.config import Settings

TEST_DATABASE_URL = "postgresql://mentora_app:mentora_dev_only@localhost:5433/mentora"
ADMIN_DATABASE_URL = "postgresql://postgres:postgres_dev_only@localhost:5433/mentora"


@dataclass
class InMemorySessionStore:
    sessions: dict[str, BrowserSession]

    def create(self, *, user_id: UUID, tenant_id: UUID, role: Role) -> tuple[str, BrowserSession]:
        session_id = secrets.token_urlsafe(16)
        session = BrowserSession(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            csrf_token=secrets.token_urlsafe(16),
        )
        self.sessions[session_id] = session
        return session_id, session

    def get(self, session_id: str) -> BrowserSession | None:
        return self.sessions.get(session_id)

    def rotate(self, session_id: str) -> tuple[str, BrowserSession] | None:
        session = self.sessions.pop(session_id, None)
        if session is None:
            return None
        return self.create(user_id=session.user_id, tenant_id=session.tenant_id, role=session.role)

    def revoke(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)


@dataclass
class InMemoryDocumentStorage:
    """Storage fake that preserves the upload contract without a MinIO dependency."""

    objects: dict[str, bytes]

    def put_pdf(self, key: str, content: bytes) -> None:
        self.objects[key] = content

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=PostgresDsn(
            TEST_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
        ),
        environment="development",
        jwt_secret=SecretStr("test-secret-not-for-production-with-at-least-32-bytes"),
        minio_access_key="minioadmin",
        minio_secret_key=SecretStr("minioadmin_dev_only"),
        cookie_secure=False,
        readiness_check_dependencies=False,
        telemetry_enabled=False,
    )


@pytest.fixture(autouse=True)
def clear_document_tables() -> Generator[None, None, None]:
    with psycopg.connect(ADMIN_DATABASE_URL) as connection:
        connection.execute(
            "TRUNCATE TABLE outbox, ingestion_job, document_version, document, knowledge_base, "
            'audit_log, membership, tenant, "user" CASCADE'
        )
        connection.commit()
    yield
    with psycopg.connect(ADMIN_DATABASE_URL) as connection:
        connection.execute(
            "TRUNCATE TABLE outbox, ingestion_job, document_version, document, knowledge_base, "
            'audit_log, membership, tenant, "user" CASCADE'
        )
        connection.commit()


def build_client(app_settings: Settings) -> TestClient:
    app = create_app(app_settings)
    app.state.session_store = InMemorySessionStore({})
    app.state.document_storage = InMemoryDocumentStorage({})
    return TestClient(app)


def csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return {"x-csrf-token": response.json()["csrf_token"]}


def signup(client: TestClient, email: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/signup",
        headers=csrf_headers(client),
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": email.split("@")[0].title(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload(client: TestClient, content: bytes = b"%PDF-1.4\nMarco 2\n") -> dict[str, Any]:
    response = client.post(
        "/api/v1/documents",
        headers=csrf_headers(client),
        files={"file": ("material.pdf", content, "application/pdf")},
    )
    assert response.status_code == 202, response.text
    return response.json()


def test_duplicate_upload_returns_existing_document_without_second_outbox_event(
    settings: Settings,
) -> None:
    with build_client(settings) as client:
        signup(client, "ana@example.com")
        first = upload(client)
        duplicate = upload(client)

    assert duplicate["id"] == first["id"]
    with psycopg.connect(ADMIN_DATABASE_URL) as connection:
        document_row = connection.execute("SELECT count(*) FROM document").fetchone()
        outbox_row = connection.execute("SELECT count(*) FROM outbox").fetchone()
    assert document_row is not None
    assert outbox_row is not None
    document_count = document_row[0]
    outbox_count = outbox_row[0]
    assert document_count == 1
    assert outbox_count == 1


def test_upload_rejects_non_pdf_magic_bytes(settings: Settings) -> None:
    with build_client(settings) as client:
        signup(client, "ana@example.com")
        response = client.post(
            "/api/v1/documents",
            headers=csrf_headers(client),
            files={"file": ("malicioso.pdf", b"not a pdf", "application/pdf")},
        )

    assert response.status_code == 415
    assert response.json()["code"] == "invalid_document_type"


def test_document_status_is_hidden_from_another_tenant(settings: Settings) -> None:
    with build_client(settings) as client_a:
        signup(client_a, "ana@example.com")
        document = upload(client_a)

    with build_client(settings) as client_b:
        signup(client_b, "bia@example.com")
        response = client_b.get(f"/api/v1/documents/{document['id']}/status")

    assert response.status_code == 404
    assert response.json()["code"] == "document_not_found"


def test_reprocess_creates_new_version_and_job_without_duplicate_document(
    settings: Settings,
) -> None:
    with build_client(settings) as client:
        signup(client, "ana@example.com")
        document = upload(client)
        response = client.post(
            f"/api/v1/documents/{document['id']}/reprocess",
            headers=csrf_headers(client),
        )
        assert response.status_code == 202, response.text

    with psycopg.connect(ADMIN_DATABASE_URL) as connection:
        document_row = connection.execute("SELECT count(*) FROM document").fetchone()
        version_row = connection.execute("SELECT count(*) FROM document_version").fetchone()
        job_row = connection.execute("SELECT count(*) FROM ingestion_job").fetchone()
    assert document_row is not None
    assert version_row is not None
    assert job_row is not None
    document_count = document_row[0]
    version_count = version_row[0]
    job_count = job_row[0]
    assert document_count == 1
    assert version_count == 2
    assert job_count == 2


def test_soft_delete_hides_document_and_emits_cleanup_event(settings: Settings) -> None:
    with build_client(settings) as client:
        signup(client, "ana@example.com")
        document = upload(client)
        response = client.delete(
            f"/api/v1/documents/{document['id']}",
            headers=csrf_headers(client),
        )
        assert response.status_code == 204
        assert client.get("/api/v1/documents").json() == []

    with psycopg.connect(ADMIN_DATABASE_URL) as connection:
        deleted_row = connection.execute(
            "SELECT deleted_at IS NOT NULL FROM document WHERE id = %s",
            (document["id"],),
        ).fetchone()
        event_row = connection.execute(
            "SELECT event_type FROM outbox ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    assert deleted_row == (True,)
    assert event_row == ("document.delete_requested",)
