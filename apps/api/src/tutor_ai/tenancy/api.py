"""Authenticated tenant endpoints that exercise RLS and RBAC."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from tutor_ai.identity import repository
from tutor_ai.identity.dependencies import CurrentPrincipal
from tutor_ai.identity.domain import Principal
from tutor_ai.identity.schemas import AuditLogResponse, MembershipResponse, TenantResponse
from tutor_ai.platform.database import database_transaction
from tutor_ai.platform.errors import ApiError
from tutor_ai.platform.rbac import require_permission

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])
AuditLogReader = Annotated[Principal, Depends(require_permission("audit_log.read"))]


@router.get("/current", response_model=TenantResponse)
def current_tenant(
    request: Request,
    principal: CurrentPrincipal,
) -> TenantResponse:
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as connection:
        tenant = repository.get_current_tenant(connection)
    if tenant is None:
        raise ApiError(404, "tenant_not_found", "Tenant ativo não encontrado.")
    return TenantResponse(id=tenant.id, name=tenant.name, slug=tenant.slug, plan=tenant.plan)


@router.get("/current/membership", response_model=MembershipResponse)
def current_membership(
    request: Request,
    principal: CurrentPrincipal,
) -> MembershipResponse:
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as connection:
        membership = repository.get_current_membership(connection, principal.user_id)
    if membership is None:
        raise ApiError(403, "membership_not_found", "Você não pertence ao tenant ativo.")
    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        tenant_id=membership.tenant_id,
        role=membership.role,
    )


@router.get("/current/audit-log", response_model=list[AuditLogResponse])
def current_audit_log(
    request: Request,
    principal: AuditLogReader,
) -> list[AuditLogResponse]:
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as connection:
        events = repository.list_audit_log(connection)
    return [AuditLogResponse.model_validate(event) for event in events]
