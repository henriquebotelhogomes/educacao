"""Domain types and enums for Classrooms and Pedagogical Modes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class PedagogicalMode(StrEnum):
    EXPLANATION = "EXPLANATION"
    SOCRATIC = "SOCRATIC"


class ClassroomRole(StrEnum):
    EDUCATOR = "educator"
    ASSISTANT = "assistant"
    STUDENT = "student"


class FlashcardStatus(StrEnum):
    PENDING = "pending"
    MASTERED = "mastered"


@dataclass(frozen=True)
class Classroom:
    id: UUID
    tenant_id: UUID
    created_by_user_id: UUID
    name: str
    code: str
    description: str | None
    pedagogical_mode: PedagogicalMode
    knowledge_base_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class ClassroomMember:
    id: UUID
    tenant_id: UUID
    classroom_id: UUID
    user_id: UUID
    role: ClassroomRole
    joined_at: datetime
    user_name: str | None = None
    user_email: str | None = None


@dataclass(frozen=True)
class LearningGapMetric:
    id: UUID
    tenant_id: UUID
    classroom_id: UUID
    topic_label: str
    document_id: UUID | None
    page_number: int | None
    question_count: int
    fallback_count: int
    negative_feedback_count: int
    recorded_date: str


@dataclass(frozen=True)
class StudentFlashcard:
    id: UUID
    tenant_id: UUID
    user_id: UUID
    classroom_id: UUID
    source_message_id: UUID | None
    front_prompt: str
    back_answer: str
    review_status: FlashcardStatus
    created_at: datetime
