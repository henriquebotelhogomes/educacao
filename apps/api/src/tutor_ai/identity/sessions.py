"""Server-side refresh sessions backed by Redis."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import cast
from uuid import UUID

from redis import Redis

from tutor_ai.identity.domain import Principal, Role


@dataclass(frozen=True)
class BrowserSession:
    """The minimum mutable state needed for refresh, logout, and CSRF."""

    user_id: UUID
    tenant_id: UUID
    role: Role
    csrf_token: str

    def principal(self, session_id: str) -> Principal:
        return Principal(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            role=self.role,
            session_id=session_id,
        )


class SessionStore:
    """Persist opaque refresh session IDs; Redis never stores the raw ID as a key."""

    def __init__(self, redis_client: Redis, ttl: timedelta) -> None:
        self._redis = redis_client
        self._ttl = ttl

    @staticmethod
    def _key(session_id: str) -> str:
        digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        return f"auth:session:{digest}"

    def create(self, *, user_id: UUID, tenant_id: UUID, role: Role) -> tuple[str, BrowserSession]:
        session_id = secrets.token_urlsafe(32)
        session = BrowserSession(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            csrf_token=secrets.token_urlsafe(32),
        )
        self._redis.setex(
            self._key(session_id),
            self._ttl,
            json.dumps(
                {
                    **asdict(session),
                    "user_id": str(session.user_id),
                    "tenant_id": str(session.tenant_id),
                    "role": session.role.value,
                }
            ),
        )
        return session_id, session

    def get(self, session_id: str) -> BrowserSession | None:
        raw_session = cast(str | None, self._redis.get(self._key(session_id)))
        if raw_session is None:
            return None
        payload = json.loads(raw_session)
        return BrowserSession(
            user_id=UUID(payload["user_id"]),
            tenant_id=UUID(payload["tenant_id"]),
            role=Role(payload["role"]),
            csrf_token=payload["csrf_token"],
        )

    def rotate(self, session_id: str) -> tuple[str, BrowserSession] | None:
        raw_session = cast(str | None, self._redis.getdel(self._key(session_id)))
        if raw_session is None:
            return None
        payload = json.loads(raw_session)
        return self.create(
            user_id=UUID(payload["user_id"]),
            tenant_id=UUID(payload["tenant_id"]),
            role=Role(payload["role"]),
        )

    def revoke(self, session_id: str) -> None:
        self._redis.delete(self._key(session_id))
