"""Public chat DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class CreateThreadRequest(BaseModel):
    title: Annotated[str | None, Field(max_length=255)] = None
    classroom_id: UUID | None = None


class ThreadResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    classroom_id: UUID | None = None
    title: str | None
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=4000)]


class FeedbackRequest(BaseModel):
    message_id: UUID
    rating: Annotated[int, Field(ge=-1, le=1)]
    reason: Annotated[str | None, Field(max_length=255)] = None
