"""Persisted tutor threads, SSE messages, and feedback."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from tutor_ai.chat import repository
from tutor_ai.chat.schemas import (
    CreateThreadRequest,
    FeedbackRequest,
    SendMessageRequest,
    ThreadResponse,
)
from tutor_ai.identity.dependencies import CurrentPrincipal
from tutor_ai.platform.database import database_transaction
from tutor_ai.platform.errors import ApiError

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
feedback_router = APIRouter(prefix="/api/v1", tags=["feedback"])


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/threads", response_model=ThreadResponse, status_code=201)
def create_thread(
    payload: CreateThreadRequest, request: Request, principal: CurrentPrincipal
) -> ThreadResponse:
    with database_transaction(
        request.app.state.settings, user_id=principal.user_id, tenant_id=principal.tenant_id
    ) as conn:
        classroom_id = payload.classroom_id
        if classroom_id is not None:
            c_row = conn.execute(
                """
                SELECT c.id, c.knowledge_base_id
                FROM classroom c
                LEFT JOIN classroom_member cm ON cm.classroom_id = c.id AND cm.user_id = %s
                WHERE c.id = %s AND c.deleted_at IS NULL
                  AND (cm.user_id IS NOT NULL OR c.created_by_user_id = %s)
                """,
                (str(principal.user_id), str(classroom_id), str(principal.user_id)),
            ).fetchone()
            if c_row is None:
                raise ApiError(403, "not_enrolled", "Você não tem acesso a esta turma.")
            kb_id = UUID(str(c_row["knowledge_base_id"]))
        else:
            row = conn.execute(
                "SELECT id FROM knowledge_base WHERE is_default AND deleted_at IS NULL LIMIT 1"
            ).fetchone()
            if row is None:
                raise ApiError(
                    409, "knowledge_base_empty", "Carregue um documento antes de iniciar o tutor."
                )
            kb_id = UUID(str(row["id"]))

        thread_id = uuid4()
        now = datetime.now(UTC)
        conn.execute(
            """
            INSERT INTO chat_thread (id, tenant_id, user_id, knowledge_base_id, classroom_id, title)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                str(thread_id),
                str(principal.tenant_id),
                str(principal.user_id),
                str(kb_id),
                str(classroom_id) if classroom_id else None,
                payload.title,
            ),
        )
    return ThreadResponse(
        id=thread_id,
        knowledge_base_id=kb_id,
        classroom_id=classroom_id,
        title=payload.title,
        created_at=now,
    )


@router.get("/threads", response_model=list[ThreadResponse])
def list_threads(
    request: Request,
    principal: CurrentPrincipal,
    classroom_id: UUID | None = None,
) -> list[ThreadResponse]:
    with database_transaction(
        request.app.state.settings, user_id=principal.user_id, tenant_id=principal.tenant_id
    ) as conn:
        if classroom_id is not None:
            rows = conn.execute(
                """
                SELECT id, knowledge_base_id, classroom_id, title, created_at FROM chat_thread
                WHERE deleted_at IS NULL AND classroom_id = %s
                ORDER BY created_at DESC
                """,
                (str(classroom_id),),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, knowledge_base_id, classroom_id, title, created_at FROM chat_thread
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
                """
            ).fetchall()
    return [
        ThreadResponse(
            id=UUID(str(row["id"])),
            knowledge_base_id=UUID(str(row["knowledge_base_id"])),
            classroom_id=UUID(str(row["classroom_id"])) if row["classroom_id"] else None,
            title=cast(str | None, row["title"]),
            created_at=cast(datetime, row["created_at"]),
        )
        for row in rows
    ]


@router.post("/threads/{thread_id}/messages")
async def send_message(
    thread_id: UUID,
    payload: SendMessageRequest,
    request: Request,
    principal: CurrentPrincipal,
) -> StreamingResponse:
    with database_transaction(
        request.app.state.settings, user_id=principal.user_id, tenant_id=principal.tenant_id
    ) as conn:
        thread = conn.execute(
            """
            SELECT knowledge_base_id, classroom_id FROM chat_thread
            WHERE id = %s AND deleted_at IS NULL
            """,
            (str(thread_id),),
        ).fetchone()
        if thread is None:
            raise ApiError(404, "thread_not_found", "Conversa não encontrada.")
        if not repository.reserve_monthly_question(
            conn,
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            limit=request.app.state.settings.free_tutor_questions_per_month,
        ):
            raise ApiError(
                403,
                "plan_limit_reached",
                "O limite mensal de perguntas do tutor foi atingido.",
                {
                    "resource": "tutor_questions",
                    "limit": request.app.state.settings.free_tutor_questions_per_month,
                },
            )
        user_message_id = uuid4()
        conn.execute(
            """
            INSERT INTO message (id, tenant_id, user_id, thread_id, role, content)
            VALUES (%s, %s, %s, %s, 'user', %s)
            """,
            (
                str(user_message_id),
                str(principal.tenant_id),
                str(principal.user_id),
                str(thread_id),
                payload.content,
            ),
        )

        pedagogical_mode = "EXPLANATION"
        if thread["classroom_id"]:
            c_row = conn.execute(
                "SELECT pedagogical_mode FROM classroom WHERE id = %s",
                (str(thread["classroom_id"]),),
            ).fetchone()
            if c_row and c_row["pedagogical_mode"]:
                pedagogical_mode = str(c_row["pedagogical_mode"])

    async def events():
        assistant_id = uuid4()
        text = ""
        result: dict[str, object] = {}
        citations: list[dict[str, object]] = []
        async for event in request.app.state.tutor_service.stream(
            payload.content,
            principal.tenant_id,
            UUID(str(thread["knowledge_base_id"])),
            pedagogical_mode=pedagogical_mode,
        ):
            if event.event == "token":
                text += str(event.data["token"])
            if event.event in {"complete", "fallback"}:
                result = event.data
            if event.event == "citations":
                citations = cast(
                    list[dict[str, object]],
                    event.data.get("citations", []),
                )
            yield _sse(event.event, event.data)
        with database_transaction(
            request.app.state.settings, user_id=principal.user_id, tenant_id=principal.tenant_id
        ) as conn:
            fallback = result.get("reason") if result else "model_unavailable"
            conn.execute(
                """
                INSERT INTO message (
                    id, tenant_id, user_id, thread_id, role, content, grounded,
                    confidence_band, fallback_reason, model, trace_id
                ) VALUES (%s,%s,%s,%s,'assistant',%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(assistant_id),
                    str(principal.tenant_id),
                    str(principal.user_id),
                    str(thread_id),
                    text or str(result.get("message", "")),
                    bool(result.get("grounded", False)),
                    result.get("confidence_band", "low"),
                    fallback,
                    result.get("model"),
                    request.headers.get("traceparent"),
                ),
            )
            for citation in citations:
                conn.execute(
                    """
                    INSERT INTO citation (
                        id, tenant_id, user_id, message_id, document_version_id, chunk_id,
                        page_number, snippet, retrieval_score
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        str(uuid4()),
                        str(principal.tenant_id),
                        str(principal.user_id),
                        str(assistant_id),
                        citation["document_version_id"],
                        citation["chunk_id"],
                        citation["page"],
                        citation["snippet"],
                        citation["score"],
                    ),
                )

            if thread["classroom_id"]:
                from tutor_ai.classes.repository import record_learning_gap_metric

                first_doc = (
                    UUID(str(citations[0]["document_id"]))
                    if citations and "document_id" in citations[0]
                    else None
                )
                first_page = (
                    int(citations[0]["page"]) if citations and "page" in citations[0] else None
                )
                record_learning_gap_metric(
                    conn,
                    tenant_id=principal.tenant_id,
                    classroom_id=UUID(str(thread["classroom_id"])),
                    topic_label=payload.content[:100],
                    document_id=first_doc,
                    page_number=first_page,
                    is_fallback=bool(fallback and fallback != ""),
                    is_negative_feedback=False,
                )
        yield _sse("complete", {"message_id": str(assistant_id), **result})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@feedback_router.post("/feedback", status_code=204)
def save_feedback(payload: FeedbackRequest, request: Request, principal: CurrentPrincipal) -> None:
    with database_transaction(
        request.app.state.settings, user_id=principal.user_id, tenant_id=principal.tenant_id
    ) as conn:
        row = conn.execute(
            """
            SELECT m.trace_id, m.content, t.classroom_id
            FROM message m
            JOIN chat_thread t ON t.id = m.thread_id
            WHERE m.id = %s
            """,
            (str(payload.message_id),),
        ).fetchone()
        if row is None:
            raise ApiError(404, "message_not_found", "Mensagem não encontrada.")
        conn.execute(
            """
            INSERT INTO feedback (id, tenant_id, user_id, message_id, rating, reason, trace_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                str(uuid4()),
                str(principal.tenant_id),
                str(principal.user_id),
                str(payload.message_id),
                payload.rating,
                payload.reason,
                row["trace_id"],
            ),
        )
        if payload.rating == -1 and row["classroom_id"]:
            from tutor_ai.classes.repository import record_learning_gap_metric

            record_learning_gap_metric(
                conn,
                tenant_id=principal.tenant_id,
                classroom_id=UUID(str(row["classroom_id"])),
                topic_label=str(row["content"])[:100],
                is_fallback=False,
                is_negative_feedback=True,
            )
