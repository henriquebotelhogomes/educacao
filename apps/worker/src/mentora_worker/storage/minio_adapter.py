"""MinIO object-storage adapter for document download."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from minio import Minio

from mentora_worker.config import WorkerSettings

logger = logging.getLogger(__name__)


class MinIOStorage:
    """Downloads documents from MinIO / S3-compatible storage."""

    def __init__(self, settings: WorkerSettings) -> None:
        parsed = urlparse(str(settings.minio_endpoint))
        endpoint = parsed.netloc  # e.g. "localhost:9000"
        secure = parsed.scheme == "https"
        self._bucket = settings.minio_bucket
        self._client = Minio(
            endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key.get_secret_value(),
            secure=secure,
        )

    def download(self, key: str) -> bytes:
        """Fetch an object from MinIO and return its raw bytes."""
        logger.debug("Downloading object '%s' from bucket '%s'.", key, self._bucket)
        response = self._client.get_object(self._bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
