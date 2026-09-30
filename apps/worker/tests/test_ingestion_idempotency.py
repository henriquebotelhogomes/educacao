"""Regression coverage for duplicate ingestion deliveries."""

from __future__ import annotations

from uuid import uuid4

from mentora_worker.ingestion import repository


class Cursor:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount
        self.statements: list[str] = []

    def __enter__(self) -> Cursor:
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def execute(self, statement: str, _: object = None) -> None:
        self.statements.append(statement)


class Connection:
    def __init__(self, rowcount: int) -> None:
        self.cursor_instance = Cursor(rowcount)
        self.committed = False

    def cursor(self) -> Cursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True


def test_terminal_ingestion_delivery_is_not_claimed_again() -> None:
    connection = Connection(rowcount=0)

    claimed = repository.claim_for_processing(
        connection,  # type: ignore[arg-type]
        uuid4(),
        uuid4(),
        uuid4(),
    )

    assert claimed is False
    assert "status = 'QUEUED'" in connection.cursor_instance.statements[-1]
