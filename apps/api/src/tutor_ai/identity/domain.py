"""Identity and session domain types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    """Roles from the V1 permission matrix."""

    OWNER = "Owner"
    ADMIN = "Admin"
    EDUCATOR = "Educator"
    STUDENT = "Student"


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    display_name: str
    password_hash: str | None
    google_subject: str | None


@dataclass(frozen=True)
class Tenant:
    id: UUID
    name: str
    slug: str
    plan: str


@dataclass(frozen=True)
class Membership:
    id: UUID
    user_id: UUID
    tenant_id: UUID
    role: Role


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    tenant_id: UUID
    role: Role
    session_id: str
