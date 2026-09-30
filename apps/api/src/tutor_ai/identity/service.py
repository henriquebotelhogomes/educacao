"""Identity use cases with explicit database and session boundaries."""

from __future__ import annotations

from uuid import UUID

from tutor_ai.identity import repository
from tutor_ai.identity.domain import Membership, Principal, Tenant, User
from tutor_ai.identity.security import hash_password, verify_password
from tutor_ai.identity.sessions import BrowserSession, SessionStore
from tutor_ai.platform.config import Settings
from tutor_ai.platform.database import database_transaction
from tutor_ai.platform.errors import ApiError


class IdentityService:
    """Coordinate signup and sign-in without exposing persistence details to routes."""

    def __init__(self, settings: Settings, session_store: SessionStore) -> None:
        self._settings = settings
        self._session_store = session_store

    def signup(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
    ) -> tuple[User, Tenant, Membership, str, BrowserSession]:
        """Create a user, personal tenant, Owner membership, and browser session atomically."""
        with database_transaction(
            self._settings,
            identity_bootstrap=True,
            auth_lookup=True,
        ) as connection:
            if repository.find_user_by_email(connection, email) is not None:
                raise ApiError(409, "email_already_registered", "Este e-mail já está cadastrado.")
            user = repository.create_user(
                connection,
                email=email,
                display_name=display_name,
                password_hash=hash_password(password),
                google_subject=None,
            )
            tenant, membership = repository.create_personal_tenant(connection, user)
            repository.append_audit_log(
                connection,
                tenant_id=tenant.id,
                user_id=user.id,
                action="user.signed_up",
                resource_type="user",
                resource_id=user.id,
            )

        session_id, session = self._session_store.create(
            user_id=user.id,
            tenant_id=tenant.id,
            role=membership.role,
        )
        return user, tenant, membership, session_id, session

    def signin(
        self,
        *,
        email: str,
        password: str,
    ) -> tuple[User, Membership, str, BrowserSession]:
        """Authenticate credentials and derive the active tenant from membership."""
        with database_transaction(self._settings, auth_lookup=True) as connection:
            user = repository.find_user_by_email(connection, email)
            if (
                user is None
                or user.password_hash is None
                or not verify_password(password, user.password_hash)
            ):
                raise ApiError(401, "invalid_credentials", "E-mail ou senha inválidos.")
            membership = repository.find_default_membership(connection, user.id)
            if membership is None:
                raise ApiError(403, "membership_missing", "Não há um tenant ativo para esta conta.")

        session_id, session = self._session_store.create(
            user_id=user.id,
            tenant_id=membership.tenant_id,
            role=membership.role,
        )
        self._append_authenticated_audit(
            user_id=user.id,
            tenant_id=membership.tenant_id,
            action="user.signed_in",
            resource_id=user.id,
        )
        return user, membership, session_id, session

    def signin_google(
        self,
        *,
        email: str,
        display_name: str,
        google_subject: str,
    ) -> tuple[User, Membership, str, BrowserSession]:
        """Create or authenticate a user after Google has verified subject and email."""
        with database_transaction(
            self._settings,
            identity_bootstrap=True,
            auth_lookup=True,
        ) as connection:
            user = repository.find_user_by_google_subject(connection, google_subject)
            membership: Membership | None
            if user is None:
                email_owner = repository.find_user_by_email(connection, email)
                if email_owner is not None:
                    raise ApiError(
                        409,
                        "email_auth_method_conflict",
                        "Este e-mail já usa outro método de autenticação.",
                    )
                user = repository.create_user(
                    connection,
                    email=email,
                    display_name=display_name,
                    password_hash=None,
                    google_subject=google_subject,
                )
                tenant, membership = repository.create_personal_tenant(connection, user)
                repository.append_audit_log(
                    connection,
                    tenant_id=tenant.id,
                    user_id=user.id,
                    action="user.signed_up_google",
                    resource_type="user",
                    resource_id=user.id,
                )
            else:
                membership = repository.find_default_membership(connection, user.id)
                if membership is None:
                    raise ApiError(
                        403,
                        "membership_missing",
                        "Não há um tenant ativo para esta conta.",
                    )

        if membership is None:
            raise ApiError(403, "membership_missing", "Não há um tenant ativo para esta conta.")
        session_id, session = self._session_store.create(
            user_id=user.id,
            tenant_id=membership.tenant_id,
            role=membership.role,
        )
        self._append_authenticated_audit(
            user_id=user.id,
            tenant_id=membership.tenant_id,
            action="user.signed_in_google",
            resource_id=user.id,
        )
        return user, membership, session_id, session

    def refresh(self, refresh_session_id: str) -> tuple[str, BrowserSession]:
        """Consume a refresh ID once and issue a replacement session."""
        rotated = self._session_store.rotate(refresh_session_id)
        if rotated is None:
            raise ApiError(401, "refresh_invalid", "Seu refresh token expirou ou já foi usado.")
        return rotated

    def logout(self, principal: Principal) -> None:
        """Revoke the server-side session and append an audit event."""
        self._session_store.revoke(principal.session_id)
        self._append_authenticated_audit(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            action="user.signed_out",
            resource_id=principal.user_id,
        )

    def _append_authenticated_audit(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
        action: str,
        resource_id: UUID,
    ) -> None:
        with database_transaction(
            self._settings,
            user_id=user_id,
            tenant_id=tenant_id,
        ) as connection:
            repository.append_audit_log(
                connection,
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                resource_type="user",
                resource_id=resource_id,
            )
