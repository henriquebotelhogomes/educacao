"""Password and JWT primitives kept outside route handlers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from tutor_ai.identity.domain import Principal, Role
from tutor_ai.platform.config import Settings
from tutor_ai.platform.errors import ApiError

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password with Argon2id."""
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return false for any invalid or mismatched Argon2 hash."""
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerifyMismatchError):
        return False


def create_access_token(principal: Principal, settings: Settings) -> str:
    """Issue the short-lived browser access token."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(principal.user_id),
        "tenant_id": str(principal.tenant_id),
        "role": principal.role.value,
        "sid": principal.session_id,
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> Principal:
    """Decode a browser access token and validate its identity claims."""
    try:
        payload = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"])
        if payload.get("typ") != "access":
            raise jwt.InvalidTokenError("Unexpected token type")
        return Principal(
            user_id=UUID(payload["sub"]),
            tenant_id=UUID(payload["tenant_id"]),
            role=Role(payload["role"]),
            session_id=str(payload["sid"]),
        )
    except (KeyError, ValueError, jwt.InvalidTokenError) as error:
        raise ApiError(
            401,
            "authentication_required",
            "Sua sessão é inválida ou expirou.",
        ) from error
