"""Dependency readiness checks without domain-specific infrastructure."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from tutor_ai.platform.config import Settings


class DependencyChecker:
    """Probe the TCP endpoints needed for the API to serve future workload."""

    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.readiness_check_dependencies
        self._timeout = settings.readiness_timeout_seconds
        self._dependencies = {
            "postgres": str(settings.database_url),
            "redis": str(settings.redis_url),
            "qdrant": str(settings.qdrant_url),
            "minio": str(settings.minio_endpoint),
        }

    @property
    def dependency_names(self) -> list[str]:
        return list(self._dependencies)

    async def unavailable_dependencies(self) -> list[str]:
        """Return dependencies whose TCP endpoint cannot be reached."""
        if not self._enabled:
            return []

        results = await asyncio.gather(
            *(self._is_available(name, url) for name, url in self._dependencies.items())
        )
        return [name for name, available in results if not available]

    async def _is_available(self, name: str, value: str) -> tuple[str, bool]:
        parsed = urlparse(value)
        default_ports = {
            "postgresql": 5432,
            "postgresql+psycopg": 5432,
            "redis": 6379,
            "http": 80,
            "https": 443,
        }
        host = parsed.hostname
        port = parsed.port or default_ports.get(parsed.scheme)
        if host is None or port is None:
            return name, False

        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self._timeout,
            )
            writer.close()
            await writer.wait_closed()
        except (OSError, TimeoutError):
            return name, False
        return name, True
