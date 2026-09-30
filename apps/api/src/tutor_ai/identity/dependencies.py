"""FastAPI dependencies for authenticated browser requests."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from tutor_ai.identity.domain import Principal
from tutor_ai.identity.security import decode_access_token
from tutor_ai.identity.sessions import SessionStore
from tutor_ai.platform.config import Settings
from tutor_ai.platform.errors import ApiError


def get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


def get_current_principal(request: Request) -> Principal:
    """Resolve the signed access cookie and require its refresh session to remain active."""
    token = request.cookies.get("mentora_access")
    if not token:
        raise ApiError(401, "authentication_required", "Faça login para continuar.")

    settings: Settings = request.app.state.settings
    principal = decode_access_token(token, settings)
    session = get_session_store(request).get(principal.session_id)
    if session is None:
        raise ApiError(401, "authentication_required", "Sua sessão expirou.")
    if (
        session.user_id != principal.user_id
        or session.tenant_id != principal.tenant_id
        or session.role != principal.role
    ):
        raise ApiError(401, "authentication_required", "Sua sessão é inválida.")
    return principal


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
