"""Create classroom, classroom_member, learning_gap_metric, and student_flashcard tables."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260803_0005"
down_revision: str | None = "20260803_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        -- 1. Tabela de Turmas / Salas de Aula (Classroom)
        CREATE TABLE classroom (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            created_by_user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            name VARCHAR(120) NOT NULL,
            code VARCHAR(10) NOT NULL UNIQUE,
            description TEXT,
            pedagogical_mode VARCHAR(20) NOT NULL DEFAULT 'EXPLANATION'
                CHECK (pedagogical_mode IN ('EXPLANATION', 'SOCRATIC')),
            knowledge_base_id UUID NOT NULL REFERENCES knowledge_base(id) ON DELETE RESTRICT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ
        );

        -- 2. Matrícula de Usuários na Turma
        CREATE TABLE classroom_member (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            classroom_id UUID NOT NULL REFERENCES classroom(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL DEFAULT 'student'
                CHECK (role IN ('educator', 'assistant', 'student')),
            joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT classroom_member_unique UNIQUE (classroom_id, user_id)
        );

        -- 3. Vínculo de Conversas à Turma
        ALTER TABLE chat_thread
            ADD COLUMN classroom_id UUID REFERENCES classroom(id) ON DELETE SET NULL;

        -- 4. Radar de Lacunas do Professor (Métricas Agregadas sem PII)
        CREATE TABLE learning_gap_metric (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            classroom_id UUID NOT NULL REFERENCES classroom(id) ON DELETE CASCADE,
            topic_label VARCHAR(150) NOT NULL,
            document_id UUID REFERENCES document(id) ON DELETE SET NULL,
            page_number INTEGER,
            question_count INTEGER NOT NULL DEFAULT 1,
            fallback_count INTEGER NOT NULL DEFAULT 0,
            negative_feedback_count INTEGER NOT NULL DEFAULT 0,
            recorded_date DATE NOT NULL DEFAULT CURRENT_DATE,
            CONSTRAINT learning_gap_metric_unique UNIQUE (classroom_id, topic_label, recorded_date)
        );

        -- 5. Caderno de Estudos / Flashcards Automáticos do Aluno
        CREATE TABLE student_flashcard (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            classroom_id UUID NOT NULL REFERENCES classroom(id) ON DELETE CASCADE,
            source_message_id UUID REFERENCES message(id) ON DELETE SET NULL,
            front_prompt TEXT NOT NULL,
            back_answer TEXT NOT NULL,
            review_status VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK (review_status IN ('pending', 'mastered')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        -- Índices para consultas de alta frequência
        CREATE INDEX classroom_tenant_code_idx ON classroom (tenant_id, code);
        CREATE INDEX classroom_member_user_idx ON classroom_member (tenant_id, user_id);
        CREATE INDEX classroom_member_classroom_idx ON classroom_member (classroom_id);
        CREATE INDEX chat_thread_classroom_idx
            ON chat_thread (tenant_id, classroom_id) WHERE deleted_at IS NULL;
        CREATE INDEX learning_gap_classroom_date_idx
            ON learning_gap_metric (classroom_id, recorded_date DESC);
        CREATE INDEX student_flashcard_user_classroom_idx
            ON student_flashcard (tenant_id, user_id, classroom_id);

        -- Ativação e reforço de RLS em todas as tabelas
        ALTER TABLE classroom ENABLE ROW LEVEL SECURITY;
        ALTER TABLE classroom FORCE ROW LEVEL SECURITY;
        ALTER TABLE classroom_member ENABLE ROW LEVEL SECURITY;
        ALTER TABLE classroom_member FORCE ROW LEVEL SECURITY;
        ALTER TABLE learning_gap_metric ENABLE ROW LEVEL SECURITY;
        ALTER TABLE learning_gap_metric FORCE ROW LEVEL SECURITY;
        ALTER TABLE student_flashcard ENABLE ROW LEVEL SECURITY;
        ALTER TABLE student_flashcard FORCE ROW LEVEL SECURITY;

        -- Políticas RLS com isolamento por tenant
        CREATE POLICY classroom_tenant_policy ON classroom
            FOR ALL USING (tenant_id = mentora_current_tenant_id())
            WITH CHECK (tenant_id = mentora_current_tenant_id());

        CREATE POLICY classroom_member_tenant_policy ON classroom_member
            FOR ALL USING (tenant_id = mentora_current_tenant_id())
            WITH CHECK (tenant_id = mentora_current_tenant_id());

        CREATE POLICY learning_gap_metric_tenant_policy ON learning_gap_metric
            FOR ALL USING (tenant_id = mentora_current_tenant_id())
            WITH CHECK (tenant_id = mentora_current_tenant_id());

        CREATE POLICY student_flashcard_tenant_policy ON student_flashcard
            FOR ALL USING (
                tenant_id = mentora_current_tenant_id()
                AND user_id = mentora_current_user_id()
            )
            WITH CHECK (
                tenant_id = mentora_current_tenant_id()
                AND user_id = mentora_current_user_id()
            );

        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mentora_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE
                    ON classroom, classroom_member, learning_gap_metric, student_flashcard
                    TO mentora_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE student_flashcard;
        DROP TABLE learning_gap_metric;
        DROP INDEX IF EXISTS chat_thread_classroom_idx;
        ALTER TABLE chat_thread DROP COLUMN IF EXISTS classroom_id;
        DROP TABLE classroom_member;
        DROP TABLE classroom;
        """
    )
