"""Pydantic v2 schemas for Classroom API requests and responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tutor_ai.classes.domain import ClassroomRole, FlashcardStatus, PedagogicalMode


class CreateClassroomRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    pedagogical_mode: PedagogicalMode = Field(default=PedagogicalMode.EXPLANATION)
    knowledge_base_id: UUID | None = Field(
        default=None,
        description="ID da Base de Conhecimento vinculada; se omitido, usa a padrão do tenant.",
    )


class UpdateClassroomRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    pedagogical_mode: PedagogicalMode | None = None


class JoinClassroomRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        min_length=4,
        max_length=10,
        description="Código curto de convite da turma (ex: 'FIS104' ou 'K9M2W7')",
    )


class ClassroomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_by_user_id: UUID
    name: str
    code: str
    description: str | None
    pedagogical_mode: PedagogicalMode
    knowledge_base_id: UUID
    created_at: datetime
    role: ClassroomRole | None = None
    member_count: int = 1


class ClassroomMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    classroom_id: UUID
    user_id: UUID
    role: ClassroomRole
    joined_at: datetime
    user_name: str | None = None
    user_email: str | None = None


class CreateFlashcardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    front_prompt: str = Field(min_length=3, max_length=2000)
    back_answer: str = Field(min_length=1, max_length=5000)
    source_message_id: UUID | None = None


class UpdateFlashcardStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_status: FlashcardStatus


class FlashcardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    classroom_id: UUID
    user_id: UUID
    source_message_id: UUID | None
    front_prompt: str
    back_answer: str
    review_status: FlashcardStatus
    created_at: datetime


class LearningGapItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_label: str
    document_id: UUID | None
    page_number: int | None
    question_count: int
    fallback_count: int
    negative_feedback_count: int


class LearningGapRadarResponse(BaseModel):
    classroom_id: UUID
    classroom_name: str
    total_questions: int
    total_fallbacks: int
    total_negative_feedbacks: int
    top_difficulties: list[LearningGapItem]
    fallback_alerts: list[LearningGapItem]
