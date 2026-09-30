"""Unit and contract tests for Classroom API, Scalar docs, and pedagogical mode orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from tutor_ai.ai.tutor import TutorService
from tutor_ai.chat.domain import RetrievedChunk
from tutor_ai.classes.domain import (
    PedagogicalMode,
)
from tutor_ai.classes.repository import CODE_ALPHABET, generate_classroom_code
from tutor_ai.classes.schemas import (
    CreateClassroomRequest,
    CreateFlashcardRequest,
    JoinClassroomRequest,
)
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


def test_scalar_docs_served_at_docs_and_api_docs() -> None:
    client = build_client()

    response_docs = client.get("/docs")
    assert response_docs.status_code == 200
    assert "text/html" in response_docs.headers["content-type"]
    assert "@scalar/api-reference" in response_docs.text
    assert "/openapi.json" in response_docs.text

    response_api_docs = client.get("/api/docs")
    assert response_api_docs.status_code == 200
    assert "text/html" in response_api_docs.headers["content-type"]
    assert "@scalar/api-reference" in response_api_docs.text


def test_openapi_schema_registers_classroom_and_radar_endpoints() -> None:
    client = build_client()
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema["paths"]

    assert "/api/v1/classes" in paths
    assert "post" in paths["/api/v1/classes"]
    assert "get" in paths["/api/v1/classes"]

    assert "/api/v1/classes/join" in paths
    assert "post" in paths["/api/v1/classes/join"]

    assert "/api/v1/classes/{classroom_id}" in paths
    assert "/api/v1/classes/{classroom_id}/members" in paths
    assert "/api/v1/classes/{classroom_id}/radar" in paths
    assert "/api/v1/classes/{classroom_id}/flashcards" in paths


def test_generate_classroom_code_uses_strict_alphabet_and_unique_constraint() -> None:
    fake_conn = MagicMock()
    # First attempt code already exists, second attempt succeeds
    fake_conn.execute.return_value.fetchone.side_effect = [("existing",), None]

    code = generate_classroom_code(fake_conn)
    assert len(code) == 6
    assert all(char in CODE_ALPHABET for char in code)
    assert "0" not in code and "O" not in code
    assert "1" not in code and "I" not in code and "L" not in code


def test_classroom_schemas_roundtrip_and_validation() -> None:
    req = CreateClassroomRequest(
        name="Física Quântica",
        description="Turma Avançada",
        pedagogical_mode=PedagogicalMode.SOCRATIC,
    )
    assert req.pedagogical_mode == PedagogicalMode.SOCRATIC
    assert req.knowledge_base_id is None

    join_req = JoinClassroomRequest(code="FIS104")
    assert join_req.code == "FIS104"

    card_req = CreateFlashcardRequest(
        front_prompt="O que é o efeito fotoelétrico?",
        back_answer="Emissão de elétrons por matéria exposta à radiação eletromagnética.",
    )
    assert card_req.source_message_id is None


@pytest.mark.anyio
async def test_socratic_mode_injects_anti_cheating_prompt_in_tutor_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts_captured: list[str] = []

    class CapturingChat:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def astream(self, prompt: str):
            prompts_captured.append(prompt)
            yield MagicMock(content="Pense no princípio da conservação.")

    fake_retriever = MagicMock()
    fake_retriever.search.return_value = [
        RetrievedChunk(
            chunk_id="chunk-1",
            document_id=uuid4(),
            document_version_id=uuid4(),
            page_number=42,
            snippet="A energia mecânica inicial é igual à final quando não há forças dissipativas.",
            score=0.92,
        )
    ]

    settings = Settings(
        environment="test",
        jwt_secret=SecretStr("test-secret-not-for-production-with-at-least-32-bytes"),
        minio_access_key="minioadmin",
        minio_secret_key=SecretStr("minioadmin_dev_only"),
        groq_api_key=SecretStr("mock-key"),
        telemetry_enabled=False,
    )

    tutor = TutorService(settings, fake_retriever)

    # Monkeypatch ChatGroq with our capturing mock
    import tutor_ai.ai.tutor as tutor_module

    monkeypatch.setattr(tutor_module, "ChatGroq", CapturingChat)

    events = [
        e
        async for e in tutor.stream(
            question="Qual é a resposta do exercício 5?",
            tenant_id=uuid4(),
            knowledge_base_id=uuid4(),
            pedagogical_mode="SOCRATIC",
        )
    ]

    assert len(prompts_captured) == 1
    socratic_prompt = prompts_captured[0]
    assert "MODO SOCRÁTICO" in socratic_prompt
    assert "NUNCA forneça a resposta final ou gabarito direto" in socratic_prompt
    assert "Página 42" in socratic_prompt

    event_types = [e.event for e in events]
    assert "token" in event_types
    assert "citations" in event_types
    assert "complete" in event_types
