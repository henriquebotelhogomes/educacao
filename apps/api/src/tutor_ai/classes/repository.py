"""PostgreSQL repository for Classrooms, Memberships, Flashcards, and Gap Radar."""

from __future__ import annotations

import secrets
from typing import Any
from uuid import UUID, uuid4

import psycopg

from tutor_ai.classes.domain import (
    Classroom,
    ClassroomMember,
    ClassroomRole,
    FlashcardStatus,
    LearningGapMetric,
    PedagogicalMode,
    StudentFlashcard,
)

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_classroom_code(
    conn: psycopg.Connection[dict[str, Any]],
    max_attempts: int = 10,
) -> str:
    """Generate a unique 6-character uppercase alphanumeric code without confusing characters."""
    for _ in range(max_attempts):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        exists = conn.execute(
            "SELECT 1 FROM classroom WHERE code = %s AND deleted_at IS NULL", (code,)
        ).fetchone()
        if not exists:
            return code
    raise RuntimeError(
        "Não foi possível gerar um código único para a turma após várias tentativas."
    )


def create_classroom(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    classroom_id: UUID,
    tenant_id: UUID,
    created_by_user_id: UUID,
    name: str,
    code: str,
    description: str | None,
    pedagogical_mode: PedagogicalMode,
    knowledge_base_id: UUID,
) -> Classroom:
    """Insert a classroom and enroll the creator as educator in a single transaction."""
    row = conn.execute(
        """
        INSERT INTO classroom (
            id, tenant_id, created_by_user_id, name, code, description,
            pedagogical_mode, knowledge_base_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, tenant_id, created_by_user_id, name, code, description,
                  pedagogical_mode, knowledge_base_id, created_at, updated_at, deleted_at
        """,
        (
            str(classroom_id),
            str(tenant_id),
            str(created_by_user_id),
            name,
            code,
            description,
            pedagogical_mode.value,
            str(knowledge_base_id),
        ),
    ).fetchone()
    assert row is not None

    # Auto-matrícula do criador como educator
    conn.execute(
        """
        INSERT INTO classroom_member (id, tenant_id, classroom_id, user_id, role)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (classroom_id, user_id) DO NOTHING
        """,
        (
            str(uuid4()),
            str(tenant_id),
            str(classroom_id),
            str(created_by_user_id),
            ClassroomRole.EDUCATOR.value,
        ),
    )

    return _row_to_classroom(row)


def get_classroom_by_id(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    classroom_id: UUID,
) -> Classroom | None:
    row = conn.execute(
        """
        SELECT id, tenant_id, created_by_user_id, name, code, description,
               pedagogical_mode, knowledge_base_id, created_at, updated_at, deleted_at
        FROM classroom
        WHERE id = %s AND deleted_at IS NULL
        """,
        (str(classroom_id),),
    ).fetchone()
    return _row_to_classroom(row) if row else None


def get_classroom_by_code(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    code: str,
) -> Classroom | None:
    row = conn.execute(
        """
        SELECT id, tenant_id, created_by_user_id, name, code, description,
               pedagogical_mode, knowledge_base_id, created_at, updated_at, deleted_at
        FROM classroom
        WHERE UPPER(code) = UPPER(%s) AND deleted_at IS NULL
        """,
        (code.strip(),),
    ).fetchone()
    return _row_to_classroom(row) if row else None


def list_user_classrooms(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    user_id: UUID,
) -> list[tuple[Classroom, ClassroomRole, int]]:
    """List classrooms the user belongs to, along with their role and member count."""
    rows = conn.execute(
        """
        SELECT c.id, c.tenant_id, c.created_by_user_id, c.name, c.code, c.description,
               c.pedagogical_mode, c.knowledge_base_id, c.created_at, c.updated_at, c.deleted_at,
               cm.role AS user_role,
               (
                   SELECT COUNT(*)::int
                   FROM classroom_member m
                   WHERE m.classroom_id = c.id
               ) AS member_count
        FROM classroom c
        JOIN classroom_member cm ON cm.classroom_id = c.id
        WHERE cm.user_id = %s AND c.deleted_at IS NULL
        ORDER BY c.created_at DESC
        """,
        (str(user_id),),
    ).fetchall()

    result: list[tuple[Classroom, ClassroomRole, int]] = []
    for r in rows:
        classroom = _row_to_classroom(r)
        role = ClassroomRole(str(r["user_role"]))
        member_count = int(r["member_count"])
        result.append((classroom, role, member_count))
    return result


def add_classroom_member(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    member_id: UUID,
    tenant_id: UUID,
    classroom_id: UUID,
    user_id: UUID,
    role: ClassroomRole = ClassroomRole.STUDENT,
) -> ClassroomMember:
    row = conn.execute(
        """
        INSERT INTO classroom_member (id, tenant_id, classroom_id, user_id, role)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (classroom_id, user_id) DO UPDATE SET role = EXCLUDED.role
        RETURNING id, tenant_id, classroom_id, user_id, role, joined_at
        """,
        (
            str(member_id),
            str(tenant_id),
            str(classroom_id),
            str(user_id),
            role.value,
        ),
    ).fetchone()
    assert row is not None
    return _row_to_member(row)


def get_user_membership(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    classroom_id: UUID,
    user_id: UUID,
) -> ClassroomMember | None:
    row = conn.execute(
        """
        SELECT cm.id, cm.tenant_id, cm.classroom_id, cm.user_id, cm.role, cm.joined_at,
               u.full_name AS user_name, u.email AS user_email
        FROM classroom_member cm
        JOIN "user" u ON u.id = cm.user_id
        WHERE cm.classroom_id = %s AND cm.user_id = %s
        """,
        (str(classroom_id), str(user_id)),
    ).fetchone()
    return _row_to_member(row) if row else None


def list_classroom_members(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    classroom_id: UUID,
) -> list[ClassroomMember]:
    rows = conn.execute(
        """
        SELECT cm.id, cm.tenant_id, cm.classroom_id, cm.user_id, cm.role, cm.joined_at,
               u.full_name AS user_name, u.email AS user_email
        FROM classroom_member cm
        JOIN "user" u ON u.id = cm.user_id
        WHERE cm.classroom_id = %s
        ORDER BY cm.joined_at ASC
        """,
        (str(classroom_id),),
    ).fetchall()
    return [_row_to_member(r) for r in rows]


def update_classroom(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    classroom_id: UUID,
    name: str | None = None,
    description: str | None = None,
    pedagogical_mode: PedagogicalMode | None = None,
) -> Classroom | None:
    updates: list[str] = []
    params: list[Any] = []

    if name is not None:
        updates.append("name = %s")
        params.append(name)
    if description is not None:
        updates.append("description = %s")
        params.append(description)
    if pedagogical_mode is not None:
        updates.append("pedagogical_mode = %s")
        params.append(pedagogical_mode.value)

    if not updates:
        return get_classroom_by_id(conn, classroom_id=classroom_id)

    updates.append("updated_at = now()")
    params.append(str(classroom_id))

    sql = f"""
        UPDATE classroom
        SET {', '.join(updates)}
        WHERE id = %s AND deleted_at IS NULL
        RETURNING id, tenant_id, created_by_user_id, name, code, description,
                  pedagogical_mode, knowledge_base_id, created_at, updated_at, deleted_at
    """
    row = conn.execute(sql, tuple(params)).fetchone()
    return _row_to_classroom(row) if row else None


# Flashcards
def create_flashcard(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    flashcard_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    classroom_id: UUID,
    front_prompt: str,
    back_answer: str,
    source_message_id: UUID | None = None,
) -> StudentFlashcard:
    row = conn.execute(
        """
        INSERT INTO student_flashcard (
            id, tenant_id, user_id, classroom_id, source_message_id,
            front_prompt, back_answer, review_status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
        RETURNING id, tenant_id, user_id, classroom_id, source_message_id,
                  front_prompt, back_answer, review_status, created_at
        """,
        (
            str(flashcard_id),
            str(tenant_id),
            str(user_id),
            str(classroom_id),
            str(source_message_id) if source_message_id else None,
            front_prompt,
            back_answer,
        ),
    ).fetchone()
    assert row is not None
    return _row_to_flashcard(row)


def list_user_flashcards(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    user_id: UUID,
    classroom_id: UUID,
) -> list[StudentFlashcard]:
    rows = conn.execute(
        """
        SELECT id, tenant_id, user_id, classroom_id, source_message_id,
               front_prompt, back_answer, review_status, created_at
        FROM student_flashcard
        WHERE user_id = %s AND classroom_id = %s
        ORDER BY created_at DESC
        """,
        (str(user_id), str(classroom_id)),
    ).fetchall()
    return [_row_to_flashcard(r) for r in rows]


def update_flashcard_status(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    flashcard_id: UUID,
    user_id: UUID,
    review_status: FlashcardStatus,
) -> StudentFlashcard | None:
    row = conn.execute(
        """
        UPDATE student_flashcard
        SET review_status = %s
        WHERE id = %s AND user_id = %s
        RETURNING id, tenant_id, user_id, classroom_id, source_message_id,
                  front_prompt, back_answer, review_status, created_at
        """,
        (review_status.value, str(flashcard_id), str(user_id)),
    ).fetchone()
    return _row_to_flashcard(row) if row else None


# Radar de Lacunas
def record_learning_gap_metric(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    tenant_id: UUID,
    classroom_id: UUID,
    topic_label: str,
    document_id: UUID | None = None,
    page_number: int | None = None,
    is_fallback: bool = False,
    is_negative_feedback: bool = False,
) -> None:
    """Upsert question metrics aggregated by classroom, topic, and date."""
    conn.execute(
        """
        INSERT INTO learning_gap_metric (
            id, tenant_id, classroom_id, topic_label, document_id, page_number,
            question_count, fallback_count, negative_feedback_count, recorded_date
        )
        VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s, CURRENT_DATE)
        ON CONFLICT (classroom_id, topic_label, recorded_date) DO UPDATE
        SET question_count = learning_gap_metric.question_count + 1,
            fallback_count = learning_gap_metric.fallback_count + EXCLUDED.fallback_count,
            negative_feedback_count = (
                learning_gap_metric.negative_feedback_count + EXCLUDED.negative_feedback_count
            )
        """,
        (
            str(uuid4()),
            str(tenant_id),
            str(classroom_id),
            topic_label[:150],
            str(document_id) if document_id else None,
            page_number,
            1 if is_fallback else 0,
            1 if is_negative_feedback else 0,
        ),
    )


def get_classroom_gap_radar(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    classroom_id: UUID,
) -> tuple[int, int, int, list[LearningGapMetric], list[LearningGapMetric]]:
    """Aggregate questions, fallbacks, and difficulties for educator dashboard."""
    totals = conn.execute(
        """
        SELECT COALESCE(SUM(question_count), 0)::int AS total_q,
               COALESCE(SUM(fallback_count), 0)::int AS total_f,
               COALESCE(SUM(negative_feedback_count), 0)::int AS total_n
        FROM learning_gap_metric
        WHERE classroom_id = %s
        """,
        (str(classroom_id),),
    ).fetchone()
    total_q = totals["total_q"] if totals else 0
    total_f = totals["total_f"] if totals else 0
    total_n = totals["total_n"] if totals else 0

    top_rows = conn.execute(
        """
        SELECT id, tenant_id, classroom_id, topic_label, document_id, page_number,
               SUM(question_count)::int AS question_count,
               SUM(fallback_count)::int AS fallback_count,
               SUM(negative_feedback_count)::int AS negative_feedback_count,
               MAX(recorded_date)::text AS recorded_date
        FROM learning_gap_metric
        WHERE classroom_id = %s
        GROUP BY id, tenant_id, classroom_id, topic_label, document_id, page_number
        ORDER BY question_count DESC
        LIMIT 10
        """,
        (str(classroom_id),),
    ).fetchall()
    top_difficulties = [_row_to_gap_metric(r) for r in top_rows]

    fallback_rows = conn.execute(
        """
        SELECT id, tenant_id, classroom_id, topic_label, document_id, page_number,
               SUM(question_count)::int AS question_count,
               SUM(fallback_count)::int AS fallback_count,
               SUM(negative_feedback_count)::int AS negative_feedback_count,
               MAX(recorded_date)::text AS recorded_date
        FROM learning_gap_metric
        WHERE classroom_id = %s AND fallback_count > 0
        GROUP BY id, tenant_id, classroom_id, topic_label, document_id, page_number
        ORDER BY fallback_count DESC
        LIMIT 10
        """,
        (str(classroom_id),),
    ).fetchall()
    fallback_alerts = [_row_to_gap_metric(r) for r in fallback_rows]

    return total_q, total_f, total_n, top_difficulties, fallback_alerts


# Helpers
def _row_to_classroom(row: dict[str, Any]) -> Classroom:
    return Classroom(
        id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        created_by_user_id=UUID(str(row["created_by_user_id"])),
        name=str(row["name"]),
        code=str(row["code"]),
        description=row["description"],
        pedagogical_mode=PedagogicalMode(str(row["pedagogical_mode"])),
        knowledge_base_id=UUID(str(row["knowledge_base_id"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row.get("deleted_at"),
    )


def _row_to_member(row: dict[str, Any]) -> ClassroomMember:
    return ClassroomMember(
        id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        classroom_id=UUID(str(row["classroom_id"])),
        user_id=UUID(str(row["user_id"])),
        role=ClassroomRole(str(row["role"])),
        joined_at=row["joined_at"],
        user_name=row.get("user_name"),
        user_email=row.get("user_email"),
    )


def _row_to_flashcard(row: dict[str, Any]) -> StudentFlashcard:
    return StudentFlashcard(
        id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        user_id=UUID(str(row["user_id"])),
        classroom_id=UUID(str(row["classroom_id"])),
        source_message_id=UUID(str(row["source_message_id"])) if row["source_message_id"] else None,
        front_prompt=str(row["front_prompt"]),
        back_answer=str(row["back_answer"]),
        review_status=FlashcardStatus(str(row["review_status"])),
        created_at=row["created_at"],
    )


def _row_to_gap_metric(row: dict[str, Any]) -> LearningGapMetric:
    return LearningGapMetric(
        id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        classroom_id=UUID(str(row["classroom_id"])),
        topic_label=str(row["topic_label"]),
        document_id=UUID(str(row["document_id"])) if row.get("document_id") else None,
        page_number=row.get("page_number"),
        question_count=int(row["question_count"]),
        fallback_count=int(row["fallback_count"]),
        negative_feedback_count=int(row["negative_feedback_count"]),
        recorded_date=str(row["recorded_date"]),
    )
