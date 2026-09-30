"""MinIO adapter for original document bytes."""

from __future__ import annotations

import io
from urllib.parse import urlparse

from minio import Minio

from tutor_ai.platform.config import Settings


class DocumentStorage:
    """Store originals once; indexed derivatives are recreated by the worker."""

    def __init__(self, settings: Settings) -> None:
        parsed = urlparse(str(settings.minio_endpoint))
        endpoint = parsed.netloc
        self._client = Minio(
            endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key.get_secret_value(),
            secure=parsed.scheme == "https",
        )
        self._bucket = settings.minio_bucket

    def put_pdf(self, key: str, content: bytes) -> None:
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(content),
            len(content),
            content_type="application/pdf",
        )

    def delete(self, key: str) -> None:
        self._client.remove_object(self._bucket, key)
