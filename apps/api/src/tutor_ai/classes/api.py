"""FastAPI router for Classrooms, Onboarding via Code, Flashcards, and Gap Radar."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Request

from tutor_ai.classes import repository
from tutor_ai.classes.domain import ClassroomRole
from tutor_ai.classes.schemas import (
    ClassroomMemberResponse,
    ClassroomResponse,
    CreateClassroomRequest,
    CreateFlashcardRequest,
    FlashcardResponse,
    JoinClassroomRequest,
    LearningGapItem,
    LearningGapRadarResponse,
    UpdateClassroomRequest,
    UpdateFlashcardStatusRequest,
)
from tutor_ai.identity.dependencies import CurrentPrincipal
from tutor_ai.platform.database import database_transaction
from tutor_ai.platform.errors import ApiError

router = APIRouter(prefix="/api/v1/classes", tags=["classes"])


@router.post("", response_model=ClassroomResponse, status_code=201)
def create_classroom(
    payload: CreateClassroomRequest,
    request: Request,
    principal: CurrentPrincipal,
) -> ClassroomResponse:
    """Create a new classroom and enroll the creator as educator."""
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as conn:
        kb_id = payload.knowledge_base_id
        if kb_id is None:
            default_kb = conn.execute(
                "SELECT id FROM knowledge_base WHERE is_default AND deleted_at IS NULL LIMIT 1"
            ).fetchone()
            if default_kb is None:
                raise ApiError(
                    409,
                    "knowledge_base_empty",
                    "Carregue um documento para inicializar a base de conhecimento "
                    "antes de criar uma turma.",
                )
            kb_id = UUID(str(default_kb["id"]))

        classroom_id = uuid4()
        code = repository.generate_classroom_code(conn)
        classroom = repository.create_classroom(
            conn,
            classroom_id=classroom_id,
            tenant_id=principal.tenant_id,
            created_by_user_id=principal.user_id,
            name=payload.name,
            code=code,
            description=payload.description,
            pedagogical_mode=payload.pedagogical_mode,
            knowledge_base_id=kb_id,
        )

        return ClassroomResponse(
            id=classroom.id,
            tenant_id=classroom.tenant_id,
            created_by_user_id=classroom.created_by_user_id,
            name=classroom.name,
            code=classroom.code,
            description=classroom.description,
            pedagogical_mode=classroom.pedagogical_mode,
            knowledge_base_id=classroom.knowledge_base_id,
            created_at=classroom.created_at,
            role=ClassroomRole.EDUCATOR,
            member_count=1,
        )


@router.get("", response_model=list[ClassroomResponse])
def list_user_classrooms(
    request: Request,
    principal: CurrentPrincipal,
) -> list[ClassroomResponse]:
    """List classrooms the authenticated user is enrolled in."""
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as conn:
        classes_with_roles = repository.list_user_classrooms(
            conn,
            user_id=principal.user_id,
        )
        return [
            ClassroomResponse(
                id=c.id,
                tenant_id=c.tenant_id,
                created_by_user_id=c.created_by_user_id,
                name=c.name,
                code=c.code,
                description=c.description,
                pedagogical_mode=c.pedagogical_mode,
                knowledge_base_id=c.knowledge_base_id,
                created_at=c.created_at,
                role=role,
                member_count=member_count,
            )
            for c, role, member_count in classes_with_roles
        ]


@router.post("/join", response_model=ClassroomResponse)
def join_classroom_by_code(
    payload: JoinClassroomRequest,
    request: Request,
    principal: CurrentPrincipal,
) -> ClassroomResponse:
    """Join a classroom using the 6-character invitation code."""
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as conn:
        classroom = repository.get_classroom_by_code(conn, code=payload.code)
        if classroom is None:
            raise ApiError(
                404, "classroom_not_found", "Turma não encontrada com o código informado."
            )

        member_id = uuid4()
        repository.add_classroom_member(
            conn,
            member_id=member_id,
            tenant_id=principal.tenant_id,
            classroom_id=classroom.id,
            user_id=principal.user_id,
            role=ClassroomRole.STUDENT,
        )

        count_row = conn.execute(
            "SELECT COUNT(*)::int AS count FROM classroom_member WHERE classroom_id = %s",
            (str(classroom.id),),
        ).fetchone()
        member_count = int(str(count_row["count"])) if count_row else 1

        return ClassroomResponse(
            id=classroom.id,
            tenant_id=classroom.tenant_id,
            created_by_user_id=classroom.created_by_user_id,
            name=classroom.name,
            code=classroom.code,
            description=classroom.description,
            pedagogical_mode=classroom.pedagogical_mode,
            knowledge_base_id=classroom.knowledge_base_id,
            created_at=classroom.created_at,
            role=ClassroomRole.STUDENT,
            member_count=member_count,
        )


@router.get("/{classroom_id}", response_model=ClassroomResponse)
def get_classroom_detail(
    classroom_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
) -> ClassroomResponse:
    """Get classroom details and verify enrollment."""
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as conn:
        classroom = repository.get_classroom_by_id(conn, classroom_id=classroom_id)
        if classroom is None:
            raise ApiError(404, "classroom_not_found", "Turma não encontrada.")

        membership = repository.get_user_membership(
            conn, classroom_id=classroom_id, user_id=principal.user_id
        )
        if membership is None and classroom.created_by_user_id != principal.user_id:
            raise ApiError(403, "not_enrolled", "Você não está matriculado nesta turma.")

        count_row = conn.execute(
            "SELECT COUNT(*)::int AS count FROM classroom_member WHERE classroom_id = %s",
            (str(classroom.id),),
        ).fetchone()
        member_count = int(str(count_row["count"])) if count_row else 1

        return ClassroomResponse(
            id=classroom.id,
            tenant_id=classroom.tenant_id,
            created_by_user_id=classroom.created_by_user_id,
            name=classroom.name,
            code=classroom.code,
            description=classroom.description,
            pedagogical_mode=classroom.pedagogical_mode,
            knowledge_base_id=classroom.knowledge_base_id,
            created_at=classroom.created_at,
            role=membership.role if membership else ClassroomRole.EDUCATOR,
            member_count=member_count,
        )


@router.patch("/{classroom_id}", response_model=ClassroomResponse)
def update_classroom(
    classroom_id: UUID,
    payload: UpdateClassroomRequest,
    request: Request,
    principal: CurrentPrincipal,
) -> ClassroomResponse:
    """Update classroom settings, including pedagogical mode (educator only)."""
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as conn:
        membership = repository.get_user_membership(
            conn, classroom_id=classroom_id, user_id=principal.user_id
        )
        if membership is None or membership.role != ClassroomRole.EDUCATOR:
            raise ApiError(
                403, "forbidden", "Apenas o educador da turma pode alterar as configurações."
            )

        classroom = repository.update_classroom(
            conn,
            classroom_id=classroom_id,
            name=payload.name,
            description=payload.description,
            pedagogical_mode=payload.pedagogical_mode,
        )
        if classroom is None:
            raise ApiError(404, "classroom_not_found", "Turma não encontrada.")

        count_row = conn.execute(
            "SELECT COUNT(*)::int AS count FROM classroom_member WHERE classroom_id = %s",
            (str(classroom.id),),
        ).fetchone()
        member_count = int(str(count_row["count"])) if count_row else 1

        return ClassroomResponse(
            id=classroom.id,
            tenant_id=classroom.tenant_id,
            created_by_user_id=classroom.created_by_user_id,
            name=classroom.name,
            code=classroom.code,
            description=classroom.description,
            pedagogical_mode=classroom.pedagogical_mode,
            knowledge_base_id=classroom.knowledge_base_id,
            created_at=classroom.created_at,
            role=ClassroomRole.EDUCATOR,
            member_count=member_count,
        )


@router.get("/{classroom_id}/members", response_model=list[ClassroomMemberResponse])
def list_classroom_members(
    classroom_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
) -> list[ClassroomMemberResponse]:
    """List enrolled members (educator only)."""
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as conn:
        membership = repository.get_user_membership(
            conn, classroom_id=classroom_id, user_id=principal.user_id
        )
        if membership is None or membership.role != ClassroomRole.EDUCATOR:
            raise ApiError(
                403, "forbidden", "Apenas o educador pode visualizar os membros da turma."
            )

        members = repository.list_classroom_members(conn, classroom_id=classroom_id)
        return [
            ClassroomMemberResponse(
                id=m.id,
                classroom_id=m.classroom_id,
                user_id=m.user_id,
                role=m.role,
                joined_at=m.joined_at,
                user_name=m.user_name,
                user_email=m.user_email,
            )
            for m in members
        ]


@router.get("/{classroom_id}/radar", response_model=LearningGapRadarResponse)
def get_learning_gap_radar(
    classroom_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
) -> LearningGapRadarResponse:
    """Get aggregated difficulty radar and fallback alerts without student PII (educator only)."""
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as conn:
        classroom = repository.get_classroom_by_id(conn, classroom_id=classroom_id)
        if classroom is None:
            raise ApiError(404, "classroom_not_found", "Turma não encontrada.")

        membership = repository.get_user_membership(
            conn, classroom_id=classroom_id, user_id=principal.user_id
        )
        if membership is None or membership.role != ClassroomRole.EDUCATOR:
            raise ApiError(
                403, "forbidden", "Apenas o educador pode visualizar o Radar de Lacunas."
            )

        total_q, total_f, total_n, top_diffs, fallbacks = repository.get_classroom_gap_radar(
            conn, classroom_id=classroom_id
        )

        return LearningGapRadarResponse(
            classroom_id=classroom.id,
            classroom_name=classroom.name,
            total_questions=total_q,
            total_fallbacks=total_f,
            total_negative_feedbacks=total_n,
            top_difficulties=[
                LearningGapItem(
                    topic_label=item.topic_label,
                    document_id=item.document_id,
                    page_number=item.page_number,
                    question_count=item.question_count,
                    fallback_count=item.fallback_count,
                    negative_feedback_count=item.negative_feedback_count,
                )
                for item in top_diffs
            ],
            fallback_alerts=[
                LearningGapItem(
                    topic_label=item.topic_label,
                    document_id=item.document_id,
                    page_number=item.page_number,
                    question_count=item.question_count,
                    fallback_count=item.fallback_count,
                    negative_feedback_count=item.negative_feedback_count,
                )
                for item in fallbacks
            ],
        )


# Flashcards
@router.post("/{classroom_id}/flashcards", response_model=FlashcardResponse, status_code=201)
def create_flashcard(
    classroom_id: UUID,
    payload: CreateFlashcardRequest,
    request: Request,
    principal: CurrentPrincipal,
) -> FlashcardResponse:
    """Create a personal study flashcard for the current student."""
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as conn:
        membership = repository.get_user_membership(
            conn, classroom_id=classroom_id, user_id=principal.user_id
        )
        if membership is None:
            raise ApiError(
                403, "not_enrolled", "Você precisa estar matriculado para criar flashcards."
            )

        card_id = uuid4()
        card = repository.create_flashcard(
            conn,
            flashcard_id=card_id,
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            classroom_id=classroom_id,
            front_prompt=payload.front_prompt,
            back_answer=payload.back_answer,
            source_message_id=payload.source_message_id,
        )

        return FlashcardResponse(
            id=card.id,
            classroom_id=card.classroom_id,
            user_id=card.user_id,
            source_message_id=card.source_message_id,
            front_prompt=card.front_prompt,
            back_answer=card.back_answer,
            review_status=card.review_status,
            created_at=card.created_at,
        )


@router.get("/{classroom_id}/flashcards", response_model=list[FlashcardResponse])
def list_student_flashcards(
    classroom_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
) -> list[FlashcardResponse]:
    """List the current student's flashcards in this classroom."""
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as conn:
        cards = repository.list_user_flashcards(
            conn,
            user_id=principal.user_id,
            classroom_id=classroom_id,
        )
        return [
            FlashcardResponse(
                id=c.id,
                classroom_id=c.classroom_id,
                user_id=c.user_id,
                source_message_id=c.source_message_id,
                front_prompt=c.front_prompt,
                back_answer=c.back_answer,
                review_status=c.review_status,
                created_at=c.created_at,
            )
            for c in cards
        ]


@router.patch("/{classroom_id}/flashcards/{flashcard_id}", response_model=FlashcardResponse)
def update_flashcard_review_status(
    classroom_id: UUID,
    flashcard_id: UUID,
    payload: UpdateFlashcardStatusRequest,
    request: Request,
    principal: CurrentPrincipal,
) -> FlashcardResponse:
    """Update a flashcard's review status (pending vs mastered)."""
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as conn:
        card = repository.update_flashcard_status(
            conn,
            flashcard_id=flashcard_id,
            user_id=principal.user_id,
            review_status=payload.review_status,
        )
        if card is None or card.classroom_id != classroom_id:
            raise ApiError(404, "flashcard_not_found", "Flashcard não encontrado.")

        return FlashcardResponse(
            id=card.id,
            classroom_id=card.classroom_id,
            user_id=card.user_id,
            source_message_id=card.source_message_id,
            front_prompt=card.front_prompt,
            back_answer=card.back_answer,
            review_status=card.review_status,
            created_at=card.created_at,
        )
