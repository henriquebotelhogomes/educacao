from fastapi.testclient import TestClient
from pydantic import SecretStr
from tutor_ai.main import create_app
from tutor_ai.platform.config import Settings


def build_client() -> TestClient:
    settings = Settings(
        readiness_check_dependencies=False,
        environment="test",
        jwt_secret=SecretStr("test-secret-not-for-production-with-at-least-32-bytes"),
        minio_access_key="minioadmin",
        minio_secret_key=SecretStr("minioadmin_dev_only"),
        telemetry_enabled=False,
    )
    return TestClient(create_app(settings))


def test_healthz_returns_process_health() -> None:
    response = build_client().get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_returns_checked_dependencies() -> None:
    response = build_client().get("/readyz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["dependencies"] == ["postgres", "redis", "qdrant", "minio"]


def test_meta_exposes_versioned_contract_and_correlation_ids() -> None:
    response = build_client().get("/api/v1/meta", headers={"x-request-id": "test-request"})

    assert response.status_code == 200
    assert response.json()["environment"] == "test"
    assert response.json()["service"] == "mentora-api"
    assert response.headers["x-request-id"] == "test-request"
