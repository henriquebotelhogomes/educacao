"""Pydantic request and response DTOs for browser identity flows."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from tutor_ai.identity.domain import Role

Password = Annotated[str, Field(min_length=12, max_length=128)]


class SignupRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: Password
    display_name: Annotated[str, Field(min_length=1, max_length=255)]


class SigninRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: Password


class SessionResponse(BaseModel):
    user_id: UUID
    tenant_id: UUID
    role: Role
    csrf_token: str


class CsrfResponse(BaseModel):
    csrf_token: str


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str


class MembershipResponse(BaseModel):
    id: UUID
    user_id: UUID
    tenant_id: UUID
    role: Role


class AuditLogResponse(BaseModel):
    id: UUID
    action: str
    resource_type: str | None
    resource_id: UUID | None
    created_at: datetime
