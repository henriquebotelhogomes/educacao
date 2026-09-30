"""Persistence operations for identity and tenancy."""

from __future__ import annotations

from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from tutor_ai.identity.domain import Membership, Role, Tenant, User

Connection = psycopg.Connection[dict[str, object]]


def _to_user(row: dict[str, object]) -> User:
    return User(
        id=UUID(str(row["id"])),
        email=str(row["email"]),
        display_name=str(row["display_name"]),
        password_hash=row["password_hash"] if isinstance(row["password_hash"], str) else None,
        google_subject=row["google_subject"] if isinstance(row["google_subject"], str) else None,
    )


def _to_tenant(row: dict[str, object]) -> Tenant:
    return Tenant(
        id=UUID(str(row["id"])),
        name=str(row["name"]),
        slug=str(row["slug"]),
        plan=str(row["plan"]),
    )


def _to_membership(row: dict[str, object]) -> Membership:
    return Membership(
        id=UUID(str(row["id"])),
        user_id=UUID(str(row["user_id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        role=Role(str(row["role"])),
    )


def find_user_by_email(connection: Connection, email: str) -> User | None:
    """Find a user during the narrowly scoped auth lookup transaction."""
    row = connection.execute(
        """
        SELECT id, email, display_name, password_hash, google_subject
        FROM "user"
        WHERE lower(email) = lower(%s) AND deleted_at IS NULL
        """,
        (email,),
    ).fetchone()
    return _to_user(row) if row else None


def find_user_by_google_subject(connection: Connection, subject: str) -> User | None:
    """Find a user from the verified Google subject."""
    row = connection.execute(
        """
        SELECT id, email, display_name, password_hash, google_subject
        FROM "user"
        WHERE google_subject = %s AND deleted_at IS NULL
        """,
        (subject,),
    ).fetchone()
    return _to_user(row) if row else None


def create_user(
    connection: Connection,
    *,
    email: str,
    display_name: str,
    password_hash: str | None,
    google_subject: str | None,
) -> User:
    """Create a user as part of the identity bootstrap transaction."""
    user = User(
        id=uuid4(),
        email=email.lower(),
        display_name=display_name,
        password_hash=password_hash,
        google_subject=google_subject,
    )
    connection.execute(
        """
        INSERT INTO "user" (id, email, display_name, password_hash, google_subject)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user.id, user.email, user.display_name, user.password_hash, user.google_subject),
    )
    return user


def create_personal_tenant(connection: Connection, user: User) -> tuple[Tenant, Membership]:
    """Create the required B2C personal tenant and Owner membership."""
    tenant = Tenant(
        id=uuid4(),
        name=f"{user.display_name} (Pessoal)",
        slug=f"pessoal-{str(user.id)[:12]}",
        plan="free",
    )
    membership = Membership(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role=Role.OWNER,
    )
    connection.execute(
        "INSERT INTO tenant (id, name, slug, plan) VALUES (%s, %s, %s, %s)",
        (tenant.id, tenant.name, tenant.slug, tenant.plan),
    )
    connection.execute(
        "INSERT INTO membership (id, user_id, tenant_id, role) VALUES (%s, %s, %s, %s)",
        (membership.id, membership.user_id, membership.tenant_id, membership.role.value),
    )
    return tenant, membership


def find_default_membership(connection: Connection, user_id: UUID) -> Membership | None:
    """Return the deterministic active tenant derived from memberships, never client input."""
    row = connection.execute(
        """
        SELECT id, user_id, tenant_id, role
        FROM membership
        WHERE user_id = %s
        ORDER BY CASE role
            WHEN 'Owner' THEN 1
            WHEN 'Admin' THEN 2
            WHEN 'Educator' THEN 3
            ELSE 4
        END, created_at
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    return _to_membership(row) if row else None


def get_current_tenant(connection: Connection) -> Tenant | None:
    """Read only the tenant admitted by RLS context."""
    row = connection.execute("SELECT id, name, slug, plan FROM tenant LIMIT 1").fetchone()
    return _to_tenant(row) if row else None


def get_current_membership(connection: Connection, user_id: UUID) -> Membership | None:
    """Read the caller's membership under the active tenant RLS context."""
    row = connection.execute(
        "SELECT id, user_id, tenant_id, role FROM membership WHERE user_id = %s LIMIT 1",
        (user_id,),
    ).fetchone()
    return _to_membership(row) if row else None


def append_audit_log(
    connection: Connection,
    *,
    tenant_id: UUID,
    user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID,
    details: dict[str, object] | None = None,
) -> None:
    """Append an immutable audit event without logging sensitive credential material."""
    connection.execute(
        """
        INSERT INTO audit_log (
            id, tenant_id, user_id, action, resource_type, resource_id, details
        ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        """,
        (
            uuid4(),
            tenant_id,
            user_id,
            action,
            resource_type,
            resource_id,
            Jsonb(details or {}),
        ),
    )


def list_audit_log(connection: Connection) -> list[dict[str, object]]:
    """List audit events visible under the current tenant RLS context."""
    return list(
        connection.execute(
            """
            SELECT id, action, resource_type, resource_id, created_at
            FROM audit_log
            ORDER BY created_at DESC
            """
        ).fetchall()
    )
