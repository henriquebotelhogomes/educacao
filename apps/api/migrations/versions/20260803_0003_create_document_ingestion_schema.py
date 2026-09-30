"""Create tenant-scoped documents, ingestion jobs, and transactional outbox."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260803_0003"
down_revision: str | None = "20260803_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create durable, RLS-protected records for idempotent document ingestion."""
    op.execute(
        """
        CREATE TABLE knowledge_base (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            name VARCHAR(255) NOT NULL,
            is_default BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ
        );
        CREATE UNIQUE INDEX knowledge_base_default_per_tenant_idx
            ON knowledge_base (tenant_id) WHERE is_default AND deleted_at IS NULL;

        CREATE TABLE document (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            knowledge_base_id UUID NOT NULL REFERENCES knowledge_base(id),
            filename VARCHAR(255) NOT NULL,
            content_hash CHAR(64) NOT NULL,
            size_bytes BIGINT NOT NULL CHECK (size_bytes > 0),
            mime_type VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ
        );
        CREATE UNIQUE INDEX document_active_content_hash_idx
            ON document (tenant_id, knowledge_base_id, content_hash)
            WHERE deleted_at IS NULL;

        CREATE TABLE document_version (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            knowledge_base_id UUID NOT NULL REFERENCES knowledge_base(id),
            document_id UUID NOT NULL REFERENCES document(id),
            version_number INTEGER NOT NULL CHECK (version_number > 0),
            storage_key VARCHAR(512) NOT NULL,
            status VARCHAR(16) NOT NULL,
            error_message VARCHAR(500),
            page_count INTEGER,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            embedding_model VARCHAR(255) NOT NULL,
            chunking_strategy_version VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            indexed_at TIMESTAMPTZ,
            CONSTRAINT document_version_status_check CHECK (
                status IN ('UPLOADED', 'QUEUED', 'PROCESSING', 'INDEXED', 'FAILED',
                           'QUARANTINED', 'SUPERSEDED')
            ),
            CONSTRAINT document_version_number_unique UNIQUE (document_id, version_number)
        );

        CREATE TABLE ingestion_job (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            knowledge_base_id UUID NOT NULL REFERENCES knowledge_base(id),
            document_id UUID NOT NULL REFERENCES document(id),
            document_version_id UUID NOT NULL REFERENCES document_version(id),
            status VARCHAR(16) NOT NULL,
            current_stage VARCHAR(32) NOT NULL DEFAULT 'queued',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            error_message VARCHAR(500),
            stream_message_id VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ,
            CONSTRAINT ingestion_job_status_check CHECK (
                status IN ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'QUARANTINED')
            )
        );
        CREATE UNIQUE INDEX ingestion_job_active_version_idx
            ON ingestion_job (document_version_id)
            WHERE status IN ('QUEUED', 'PROCESSING');

        CREATE TABLE outbox (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            aggregate_id UUID NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            published_at TIMESTAMPTZ
        );
        CREATE INDEX outbox_unpublished_idx ON outbox (created_at) WHERE published_at IS NULL;

        CREATE FUNCTION mentora_worker_active() RETURNS BOOLEAN
        LANGUAGE SQL STABLE
        AS $$
            SELECT current_setting('app.worker', true) = 'true'
        $$;

        ALTER TABLE knowledge_base ENABLE ROW LEVEL SECURITY;
        ALTER TABLE knowledge_base FORCE ROW LEVEL SECURITY;
        ALTER TABLE document ENABLE ROW LEVEL SECURITY;
        ALTER TABLE document FORCE ROW LEVEL SECURITY;
        ALTER TABLE document_version ENABLE ROW LEVEL SECURITY;
        ALTER TABLE document_version FORCE ROW LEVEL SECURITY;
        ALTER TABLE ingestion_job ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ingestion_job FORCE ROW LEVEL SECURITY;
        ALTER TABLE outbox ENABLE ROW LEVEL SECURITY;
        ALTER TABLE outbox FORCE ROW LEVEL SECURITY;

        CREATE POLICY knowledge_base_tenant_policy ON knowledge_base
            FOR ALL USING (tenant_id = mentora_current_tenant_id())
            WITH CHECK (tenant_id = mentora_current_tenant_id());
        CREATE POLICY document_tenant_policy ON document
            FOR ALL USING (tenant_id = mentora_current_tenant_id())
            WITH CHECK (tenant_id = mentora_current_tenant_id());
        CREATE POLICY document_version_tenant_policy ON document_version
            FOR ALL USING (tenant_id = mentora_current_tenant_id())
            WITH CHECK (tenant_id = mentora_current_tenant_id());
        CREATE POLICY ingestion_job_tenant_policy ON ingestion_job
            FOR ALL USING (tenant_id = mentora_current_tenant_id())
            WITH CHECK (tenant_id = mentora_current_tenant_id());
        CREATE POLICY outbox_api_policy ON outbox
            FOR INSERT WITH CHECK (tenant_id = mentora_current_tenant_id());
        CREATE POLICY outbox_worker_policy ON outbox
            FOR ALL USING (mentora_worker_active())
            WITH CHECK (mentora_worker_active());

        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mentora_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE
                    ON knowledge_base, document, document_version, ingestion_job TO mentora_app;
                GRANT SELECT, INSERT, UPDATE ON outbox TO mentora_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Remove document ingestion persistence and its RLS helper."""
    op.execute(
        """
        DROP TABLE outbox;
        DROP TABLE ingestion_job;
        DROP TABLE document_version;
        DROP TABLE document;
        DROP TABLE knowledge_base;
        DROP FUNCTION mentora_worker_active();
        """
    )
