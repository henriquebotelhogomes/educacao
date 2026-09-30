from __future__ import annotations

import asyncio
from uuid import uuid4

from pydantic import SecretStr
from tutor_ai.ai.tutor import TutorEvent, TutorService
from tutor_ai.chat.domain import RetrievedChunk
from tutor_ai.platform.config import Settings


class EmptyRetriever:
    def search(self, *_: object) -> list[RetrievedChunk]:
        return []


def test_tutor_falls_back_without_retrieved_evidence() -> None:
    settings = Settings(
        environment="test",
        jwt_secret=SecretStr("test-secret-not-for-production-with-at-least-32-bytes"),
        minio_access_key="minioadmin",
        minio_secret_key=SecretStr("minioadmin_dev_only"),
        cookie_secure=False,
        telemetry_enabled=False,
    )
    service = TutorService(settings, EmptyRetriever())

    async def collect() -> list[TutorEvent]:
        return [event async for event in service.stream("O que é fotossíntese?", uuid4(), uuid4())]

    events = asyncio.run(collect())

    assert [event.event for event in events] == ["fallback", "confidence"]
    assert events[0].data["reason"] == "no_evidence"
    assert events[1].data["band"] == "low"
