"""Create identity, tenancy, audit, and Row-Level Security foundations."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260803_0002"
down_revision: str | None = "20260803_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create the minimal multi-tenant identity schema with RLS policies."""
    op.execute(
        """
        CREATE TABLE "user" (
            id UUID PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255),
            display_name VARCHAR(255) NOT NULL,
            google_subject VARCHAR(255) UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT user_email_unique UNIQUE (email),
            CONSTRAINT user_auth_method_check
                CHECK (password_hash IS NOT NULL OR google_subject IS NOT NULL)
        );

        CREATE TABLE tenant (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL UNIQUE,
            plan VARCHAR(32) NOT NULL DEFAULT 'free',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE membership (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES "user"(id),
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            role VARCHAR(16) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT membership_user_tenant_unique UNIQUE (user_id, tenant_id),
            CONSTRAINT membership_role_check
                CHECK (role IN ('Owner', 'Admin', 'Educator', 'Student'))
        );

        CREATE TABLE audit_log (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            user_id UUID REFERENCES "user"(id),
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(64),
            resource_id UUID,
            details JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX membership_tenant_id_idx ON membership (tenant_id);
        CREATE INDEX membership_user_id_idx ON membership (user_id);
        CREATE INDEX audit_log_tenant_created_at_idx ON audit_log (tenant_id, created_at DESC);

        CREATE FUNCTION mentora_current_user_id() RETURNS UUID
        LANGUAGE SQL STABLE
        AS $$
            SELECT NULLIF(current_setting('app.current_user_id', true), '')::UUID
        $$;

        CREATE FUNCTION mentora_current_tenant_id() RETURNS UUID
        LANGUAGE SQL STABLE
        AS $$
            SELECT NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        $$;

        CREATE FUNCTION mentora_identity_bootstrap_active() RETURNS BOOLEAN
        LANGUAGE SQL STABLE
        AS $$
            SELECT current_setting('app.identity_bootstrap', true) = 'true'
        $$;

        CREATE FUNCTION mentora_auth_lookup_active() RETURNS BOOLEAN
        LANGUAGE SQL STABLE
        AS $$
            SELECT current_setting('app.auth_lookup', true) = 'true'
        $$;

        ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;
        ALTER TABLE "user" FORCE ROW LEVEL SECURITY;
        ALTER TABLE tenant ENABLE ROW LEVEL SECURITY;
        ALTER TABLE tenant FORCE ROW LEVEL SECURITY;
        ALTER TABLE membership ENABLE ROW LEVEL SECURITY;
        ALTER TABLE membership FORCE ROW LEVEL SECURITY;
        ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
        ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;

        CREATE POLICY user_select_policy ON "user"
            FOR SELECT USING (
                id = mentora_current_user_id() OR mentora_auth_lookup_active()
            );
        CREATE POLICY user_insert_policy ON "user"
            FOR INSERT WITH CHECK (mentora_identity_bootstrap_active());
        CREATE POLICY user_update_policy ON "user"
            FOR UPDATE USING (id = mentora_current_user_id())
            WITH CHECK (id = mentora_current_user_id());

        CREATE POLICY tenant_select_policy ON tenant
            FOR SELECT USING (id = mentora_current_tenant_id());
        CREATE POLICY tenant_insert_policy ON tenant
            FOR INSERT WITH CHECK (mentora_identity_bootstrap_active());
        CREATE POLICY tenant_update_policy ON tenant
            FOR UPDATE USING (id = mentora_current_tenant_id())
            WITH CHECK (id = mentora_current_tenant_id());

        CREATE POLICY membership_select_policy ON membership
            FOR SELECT USING (
                tenant_id = mentora_current_tenant_id() OR mentora_auth_lookup_active()
            );
        CREATE POLICY membership_insert_policy ON membership
            FOR INSERT WITH CHECK (mentora_identity_bootstrap_active());

        CREATE POLICY audit_log_select_policy ON audit_log
            FOR SELECT USING (tenant_id = mentora_current_tenant_id());
        CREATE POLICY audit_log_insert_policy ON audit_log
            FOR INSERT WITH CHECK (
                tenant_id = mentora_current_tenant_id()
                OR mentora_identity_bootstrap_active()
            );

        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mentora_app') THEN
                GRANT SELECT, INSERT, UPDATE ON "user", tenant, membership TO mentora_app;
                GRANT SELECT, INSERT ON audit_log TO mentora_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Remove all identity tables, policies, and helper functions."""
    op.execute(
        """
        DROP TABLE audit_log;
        DROP TABLE membership;
        DROP TABLE tenant;
        DROP TABLE "user";
        DROP FUNCTION mentora_auth_lookup_active();
        DROP FUNCTION mentora_identity_bootstrap_active();
        DROP FUNCTION mentora_current_tenant_id();
        DROP FUNCTION mentora_current_user_id();
        """
    )
