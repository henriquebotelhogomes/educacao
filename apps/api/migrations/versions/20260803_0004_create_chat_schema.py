"""Create tutor threads, messages, citations, feedback, and query metering."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260803_0004"
down_revision: str | None = "20260803_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE chat_thread (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            user_id UUID NOT NULL REFERENCES "user"(id),
            knowledge_base_id UUID NOT NULL REFERENCES knowledge_base(id),
            title VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ
        );

        CREATE TABLE message (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            user_id UUID NOT NULL REFERENCES "user"(id),
            thread_id UUID NOT NULL REFERENCES chat_thread(id),
            role VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            grounded BOOLEAN,
            confidence_band VARCHAR(16) CHECK (confidence_band IN ('high', 'medium', 'low')),
            fallback_reason VARCHAR(255),
            model VARCHAR(128),
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            trace_id VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE citation (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            user_id UUID NOT NULL REFERENCES "user"(id),
            message_id UUID NOT NULL REFERENCES message(id),
            document_version_id UUID NOT NULL REFERENCES document_version(id),
            chunk_id VARCHAR(255) NOT NULL,
            page_number INTEGER NOT NULL,
            snippet TEXT NOT NULL,
            retrieval_score DOUBLE PRECISION,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE feedback (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            user_id UUID NOT NULL REFERENCES "user"(id),
            message_id UUID NOT NULL REFERENCES message(id),
            rating SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
            reason VARCHAR(255),
            trace_id VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT feedback_user_message_unique UNIQUE (user_id, message_id)
        );

        CREATE TABLE usage_event (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            user_id UUID NOT NULL REFERENCES "user"(id),
            event_type VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX chat_thread_user_idx ON chat_thread (tenant_id, user_id, created_at DESC);
        CREATE INDEX message_thread_idx ON message (thread_id, created_at);
        CREATE INDEX citation_message_idx ON citation (message_id);
        CREATE INDEX usage_event_tenant_type_idx ON usage_event (tenant_id, event_type, created_at);

        ALTER TABLE chat_thread ENABLE ROW LEVEL SECURITY;
        ALTER TABLE chat_thread FORCE ROW LEVEL SECURITY;
        ALTER TABLE message ENABLE ROW LEVEL SECURITY;
        ALTER TABLE message FORCE ROW LEVEL SECURITY;
        ALTER TABLE citation ENABLE ROW LEVEL SECURITY;
        ALTER TABLE citation FORCE ROW LEVEL SECURITY;
        ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
        ALTER TABLE feedback FORCE ROW LEVEL SECURITY;
        ALTER TABLE usage_event ENABLE ROW LEVEL SECURITY;
        ALTER TABLE usage_event FORCE ROW LEVEL SECURITY;

        CREATE POLICY chat_thread_owner_policy ON chat_thread
            FOR ALL USING (
                tenant_id = mentora_current_tenant_id()
                AND user_id = mentora_current_user_id()
            )
            WITH CHECK (
                tenant_id = mentora_current_tenant_id()
                AND user_id = mentora_current_user_id()
            );
        CREATE POLICY message_owner_policy ON message
            FOR ALL USING (
                tenant_id = mentora_current_tenant_id()
                AND user_id = mentora_current_user_id()
            )
            WITH CHECK (
                tenant_id = mentora_current_tenant_id()
                AND user_id = mentora_current_user_id()
            );
        CREATE POLICY citation_owner_policy ON citation
            FOR ALL USING (
                tenant_id = mentora_current_tenant_id()
                AND user_id = mentora_current_user_id()
            )
            WITH CHECK (
                tenant_id = mentora_current_tenant_id()
                AND user_id = mentora_current_user_id()
            );
        CREATE POLICY feedback_owner_policy ON feedback
            FOR ALL USING (
                tenant_id = mentora_current_tenant_id()
                AND user_id = mentora_current_user_id()
            )
            WITH CHECK (
                tenant_id = mentora_current_tenant_id()
                AND user_id = mentora_current_user_id()
            );
        CREATE POLICY usage_event_tenant_policy ON usage_event
            FOR ALL USING (tenant_id = mentora_current_tenant_id())
            WITH CHECK (tenant_id = mentora_current_tenant_id());

        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mentora_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE
                    ON chat_thread, message, citation, feedback, usage_event TO mentora_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE usage_event;
        DROP TABLE feedback;
        DROP TABLE citation;
        DROP TABLE message;
        DROP TABLE chat_thread;
        """
    )
