"""Permission matrix defined by specs/12-execution-plan.md section 4.2."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from tutor_ai.identity.dependencies import get_current_principal
from tutor_ai.identity.domain import Principal, Role
from tutor_ai.platform.errors import ApiError

PERMISSIONS: dict[str, frozenset[Role]] = {
    "tenant.manage": frozenset({Role.OWNER}),
    "membership.manage": frozenset({Role.OWNER, Role.ADMIN}),
    "knowledge_base.create": frozenset({Role.OWNER, Role.ADMIN, Role.EDUCATOR}),
    "document.manage": frozenset({Role.OWNER, Role.ADMIN, Role.EDUCATOR}),
    "document.read": frozenset({Role.OWNER, Role.ADMIN, Role.EDUCATOR, Role.STUDENT}),
    "tutor.chat": frozenset({Role.OWNER, Role.ADMIN, Role.EDUCATOR, Role.STUDENT}),
    "exercise.generate": frozenset({Role.OWNER, Role.ADMIN, Role.EDUCATOR}),
    "analytics.read": frozenset({Role.OWNER, Role.ADMIN, Role.EDUCATOR}),
    "audit_log.read": frozenset({Role.OWNER, Role.ADMIN}),
}


def require_permission(permission: str) -> Callable[[Principal], Principal]:
    """Create a FastAPI dependency enforcing one documented RBAC permission."""
    allowed_roles = PERMISSIONS[permission]

    def verify(
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Principal:
        if principal.role not in allowed_roles:
            raise ApiError(403, "forbidden", "Você não tem permissão para esta ação.")
        return principal

    return verify
