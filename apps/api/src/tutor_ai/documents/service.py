"""Document upload, deduplication, reprocessing, and deletion use cases."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from uuid import UUID, uuid4

from psycopg.errors import UniqueViolation

from tutor_ai.documents import repository
from tutor_ai.documents.domain import DocumentRecord, DocumentVersion, IngestionJob
from tutor_ai.documents.repository import Connection
from tutor_ai.documents.storage import DocumentStorage
from tutor_ai.platform.config import Settings
from tutor_ai.platform.database import database_transaction
from tutor_ai.platform.errors import ApiError

SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._ -]")


@dataclass(frozen=True)
class UploadResult:
    document: DocumentRecord
    version: DocumentVersion
    job: IngestionJob
    duplicate: bool


class DocumentService:
    """Perform synchronous admission; durable asynchronous work begins through the outbox."""

    def __init__(self, settings: Settings, storage: DocumentStorage) -> None:
        self._settings = settings
        self._storage = storage

    def upload(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        filename: str,
        content: bytes,
    ) -> UploadResult:
        """Validate, hash, persist and enqueue an original PDF exactly once."""
        normalized_filename = self._validate_pdf(filename, content)
        content_hash = hashlib.sha256(content).hexdigest()

        with database_transaction(
            self._settings,
            user_id=user_id,
            tenant_id=tenant_id,
        ) as connection:
            knowledge_base_id = repository.get_or_create_default_knowledge_base(
                connection, tenant_id
            )
            duplicate = repository.find_active_document_by_hash(connection, content_hash)
            if duplicate is not None:
                document, version, job = duplicate
                return UploadResult(document, version, job, duplicate=True)
            self._enforce_document_quota(connection)
            document_id = uuid4()
            storage_key = (
                f"tenants/{tenant_id}/documents/{document_id}/versions/1/{content_hash}.pdf"
            )

        self._storage.put_pdf(storage_key, content)
        try:
            with database_transaction(
                self._settings,
                user_id=user_id,
                tenant_id=tenant_id,
            ) as connection:
                duplicate = repository.find_active_document_by_hash(connection, content_hash)
                if duplicate is not None:
                    document, version, job = duplicate
                    return UploadResult(document, version, job, duplicate=True)
                document, version, job = repository.create_document_ingestion(
                    connection,
                    tenant_id=tenant_id,
                    knowledge_base_id=knowledge_base_id,
                    filename=normalized_filename,
                    content_hash=content_hash,
                    size_bytes=len(content),
                    storage_key=storage_key,
                )
                return UploadResult(document, version, job, duplicate=False)
        except UniqueViolation:
            with database_transaction(
                self._settings,
                user_id=user_id,
                tenant_id=tenant_id,
            ) as connection:
                duplicate = repository.find_active_document_by_hash(connection, content_hash)
                if duplicate is None:
                    raise
                document, version, job = duplicate
                return UploadResult(document, version, job, duplicate=True)

    def reprocess(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        document_id: UUID,
    ) -> tuple[DocumentVersion, IngestionJob]:
        with database_transaction(
            self._settings,
            user_id=user_id,
            tenant_id=tenant_id,
        ) as connection:
            try:
                return repository.reprocess_document(connection, document_id)
            except LookupError as error:
                raise ApiError(404, "document_not_found", "Documento não encontrado.") from error

    def delete(self, *, tenant_id: UUID, user_id: UUID, document_id: UUID) -> None:
        with database_transaction(
            self._settings,
            user_id=user_id,
            tenant_id=tenant_id,
        ) as connection:
            if not repository.soft_delete_document(connection, document_id):
                raise ApiError(404, "document_not_found", "Documento não encontrado.")

    def _validate_pdf(self, filename: str, content: bytes) -> str:
        if not content.startswith(b"%PDF-"):
            raise ApiError(415, "invalid_document_type", "Envie um arquivo PDF válido.")
        if len(content) > self._settings.document_max_size_bytes:
            raise ApiError(
                413,
                "file_too_large",
                f"O arquivo excede o limite de {self._settings.document_max_size_bytes} bytes.",
            )
        sanitized_filename = SAFE_FILENAME.sub("_", filename).strip(" .")
        if not sanitized_filename.lower().endswith(".pdf") or not sanitized_filename:
            raise ApiError(415, "invalid_document_name", "O nome do arquivo deve terminar em .pdf.")
        return sanitized_filename

    def _enforce_document_quota(self, connection: Connection) -> None:
        document_count = repository.count_active_documents(connection)
        if document_count >= self._settings.free_document_limit:
            raise ApiError(
                403,
                "plan_limit_reached",
                "O limite de documentos ativos do plano foi atingido.",
                {
                    "resource": "active_documents",
                    "limit": self._settings.free_document_limit,
                },
            )
