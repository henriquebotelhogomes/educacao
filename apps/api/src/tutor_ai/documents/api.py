"""Tenant-safe document admission and status endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from tutor_ai.documents import repository
from tutor_ai.documents.domain import DocumentVersion, IngestionJob
from tutor_ai.documents.schemas import DocumentResponse, DocumentStatusResponse
from tutor_ai.documents.service import DocumentService, UploadResult
from tutor_ai.identity.dependencies import CurrentPrincipal
from tutor_ai.identity.domain import Principal
from tutor_ai.platform.database import database_transaction
from tutor_ai.platform.errors import ApiError
from tutor_ai.platform.rbac import require_permission

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
DocumentManager = Annotated[Principal, Depends(require_permission("document.manage"))]


def _service(request: Request) -> DocumentService:
    return DocumentService(request.app.state.settings, request.app.state.document_storage)


def _response(
    document_id: UUID,
    knowledge_base_id: UUID,
    filename: str,
    content_hash: str,
    size_bytes: int,
    version: DocumentVersion,
    job: IngestionJob,
    created_at: datetime,
) -> DocumentResponse:
    return DocumentResponse(
        id=document_id,
        knowledge_base_id=knowledge_base_id,
        filename=filename,
        content_hash=content_hash,
        size_bytes=size_bytes,
        status=version.status,
        version_id=version.id,
        ingestion_job_id=job.id,
        error_message=version.error_message,
        created_at=created_at,
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File(description="PDF original")],
    principal: DocumentManager,
) -> DocumentResponse:
    content = await file.read(request.app.state.settings.document_max_size_bytes + 1)
    result: UploadResult = await run_in_threadpool(
        _service(request).upload,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        filename=file.filename or "documento.pdf",
        content=content,
    )
    response = _response(
        result.document.id,
        result.document.knowledge_base_id,
        result.document.filename,
        result.document.content_hash,
        result.document.size_bytes,
        result.version,
        result.job,
        datetime.now().astimezone(),
    )
    if result.duplicate:
        return response
    return response


@router.get("", response_model=list[DocumentResponse])
def list_tenant_documents(request: Request, principal: CurrentPrincipal) -> list[DocumentResponse]:
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as connection:
        rows = repository.list_documents(connection)
    return [
        DocumentResponse(
            id=UUID(str(row["id"])),
            knowledge_base_id=UUID(str(row["knowledge_base_id"])),
            filename=str(row["filename"]),
            content_hash=str(row["content_hash"]),
            size_bytes=int(row["size_bytes"]),
            status=row["status"],
            version_id=UUID(str(row["version_id"])),
            ingestion_job_id=UUID(str(row["ingestion_job_id"])),
            error_message=row["error_message"] if isinstance(row["error_message"], str) else None,
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def document_status(
    document_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
) -> DocumentStatusResponse:
    with database_transaction(
        request.app.state.settings,
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
    ) as connection:
        job = repository.get_document_job(connection, document_id)
    if job is None:
        raise ApiError(404, "document_not_found", "Documento não encontrado.")
    return DocumentStatusResponse(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        current_stage=job.current_stage,
        attempt_count=job.attempt_count,
        error_message=job.error_message,
        updated_at=job.updated_at,
    )


@router.post("/{document_id}/reprocess", response_model=DocumentStatusResponse, status_code=202)
def reprocess_document(
    document_id: UUID,
    request: Request,
    principal: DocumentManager,
) -> DocumentStatusResponse:
    version, job = _service(request).reprocess(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        document_id=document_id,
    )
    return DocumentStatusResponse(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        current_stage=job.current_stage,
        attempt_count=job.attempt_count,
        error_message=version.error_message,
        updated_at=job.updated_at,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    request: Request,
    principal: DocumentManager,
) -> None:
    _service(request).delete(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        document_id=document_id,
    )
