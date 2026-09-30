"""Identity integration tests against the PostgreSQL instance from Docker Compose."""

from __future__ import annotations

import os
import secrets
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import PostgresDsn, SecretStr
from tutor_ai.identity.domain import Role
from tutor_ai.identity.security import create_access_token
from tutor_ai.identity.sessions import BrowserSession
from tutor_ai.main import create_app
from tutor_ai.platform.config import Settings
from tutor_ai.platform.database import database_transaction

TEST_DATABASE_URL = os.getenv(
    "MENTORA_TEST_DATABASE_URL",
    "postgresql://mentora_app:mentora_dev_only@localhost:5433/mentora",
)
ADMIN_DATABASE_URL = os.getenv(
    "MENTORA_ADMIN_DATABASE_URL",
    "postgresql://postgres:postgres_dev_only@localhost:5433/mentora",
)


@dataclass
class InMemorySessionStore:
    """Deterministic Redis substitute; PostgreSQL remains real for integration coverage."""

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
class InMemoryRedis:
    values: dict[str, str]

    def setex(self, key: str, _: int, value: str) -> None:
        self.values[key] = value

    def getdel(self, key: str) -> str | None:
        return self.values.pop(key, None)

    def close(self) -> None:
        pass


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
def clear_identity_tables() -> Generator[None, None, None]:
    """Reset test rows with the local Postgres administrator, outside the app role."""
    with psycopg.connect(ADMIN_DATABASE_URL) as connection:
        connection.execute('TRUNCATE TABLE audit_log, membership, tenant, "user" CASCADE')
        connection.commit()
    yield
    with psycopg.connect(ADMIN_DATABASE_URL) as connection:
        connection.execute('TRUNCATE TABLE audit_log, membership, tenant, "user" CASCADE')
        connection.commit()


@pytest.fixture
def client(settings: Settings) -> Generator[TestClient, None, None]:
    app = create_app(settings)
    app.state.session_store = InMemorySessionStore({})
    with TestClient(app) as test_client:
        yield test_client


def csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return {"x-csrf-token": response.json()["csrf_token"]}


def signup(client: TestClient, email: str, display_name: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/signup",
        headers=csrf_headers(client),
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": display_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_signup_creates_personal_tenant_owner_membership_and_http_only_cookies(
    client: TestClient,
) -> None:
    session = signup(client, "ana@example.com", "Ana")

    assert session["role"] == Role.OWNER.value
    assert client.cookies.get("mentora_access") is not None
    assert client.cookies.get("mentora_refresh") is not None
    assert client.cookies.get("mentora_csrf") == session["csrf_token"]

    tenant_response = client.get("/api/v1/tenants/current")
    assert tenant_response.status_code == 200
    assert tenant_response.json()["id"] == session["tenant_id"]
    assert tenant_response.json()["name"] == "Ana (Pessoal)"

    membership_response = client.get("/api/v1/tenants/current/membership")
    assert membership_response.status_code == 200
    assert membership_response.json()["role"] == Role.OWNER.value


def test_mutations_require_double_submit_csrf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "ana@example.com",
            "password": "correct-horse-battery-staple",
            "display_name": "Ana",
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_invalid"


def test_google_oauth_is_disabled_without_provider_configuration(client: TestClient) -> None:
    response = client.get("/api/v1/auth/oauth/google")

    assert response.status_code == 503
    assert response.json()["code"] == "google_oauth_not_configured"


def test_google_oauth_state_is_bound_to_the_initiating_browser(settings: Settings) -> None:
    oauth_settings = settings.model_copy(
        update={
            "google_oauth_client_id": "google-client",
            "google_oauth_client_secret": SecretStr("google-secret"),
            "google_oauth_redirect_uri": "http://localhost/api/v1/auth/oauth/google/callback",
        }
    )
    app = create_app(oauth_settings)
    app.state.redis = InMemoryRedis({})

    with TestClient(app) as initiating_browser:
        response = initiating_browser.get("/api/v1/auth/oauth/google", follow_redirects=False)

        assert response.status_code == 307
        state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
        assert initiating_browser.cookies.get("mentora_oauth_state") == state

        with TestClient(app) as different_browser:
            callback = different_browser.get(
                "/api/v1/auth/oauth/google/callback",
                params={"code": "attacker-code", "state": state},
                follow_redirects=False,
            )

        assert callback.status_code == 403
        assert callback.json()["code"] == "oauth_state_invalid"


def test_refresh_rotation_rejects_replay(client: TestClient) -> None:
    signup(client, "ana@example.com", "Ana")
    old_refresh = client.cookies.get("mentora_refresh")
    assert old_refresh is not None

    response = client.post("/api/v1/auth/refresh", headers=csrf_headers(client))
    assert response.status_code == 200
    assert client.cookies.get("mentora_refresh") != old_refresh

    client.cookies.set("mentora_refresh", old_refresh, path="/api/v1/auth")
    replay = client.post("/api/v1/auth/refresh", headers=csrf_headers(client))
    assert replay.status_code == 401
    assert replay.json()["code"] == "refresh_invalid"


def test_rls_blocks_cross_tenant_read_and_update(settings: Settings, client: TestClient) -> None:
    tenant_a = signup(client, "ana@example.com", "Ana")["tenant_id"]
    app_b = create_app(settings)
    app_b.state.session_store = InMemorySessionStore({})
    with TestClient(app_b) as client_b:
        tenant_b = signup(client_b, "bia@example.com", "Bia")["tenant_id"]

    with database_transaction(
        settings,
        user_id=UUID(tenant_a),
        tenant_id=UUID(tenant_a),
    ) as connection:
        cross_tenant_read = connection.execute(
            "SELECT id FROM tenant WHERE id = %s",
            (tenant_b,),
        ).fetchone()
        cross_tenant_update = connection.execute(
            "UPDATE tenant SET name = 'não deve atualizar' WHERE id = %s",
            (tenant_b,),
        )
        assert cross_tenant_read is None
        assert cross_tenant_update.rowcount == 0


def test_rbac_denies_audit_log_to_student(settings: Settings, client: TestClient) -> None:
    session = signup(client, "ana@example.com", "Ana")
    user_id = UUID(session["user_id"])
    tenant_id = UUID(session["tenant_id"])
    app = cast(FastAPI, client.app)
    session_id, browser_session = app.state.session_store.create(
        user_id=user_id,
        tenant_id=tenant_id,
        role=Role.STUDENT,
    )
    student_access = create_access_token(browser_session.principal(session_id), settings)
    client.cookies.set("mentora_access", student_access, path="/")

    response = client.get("/api/v1/tenants/current/audit-log")

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
