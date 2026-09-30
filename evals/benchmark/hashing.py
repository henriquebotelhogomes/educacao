"""Deterministic hashing helpers for ADR-018 benchmark inputs."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
from enum import Enum
from typing import Any

from pydantic import BaseModel


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=False)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    if isinstance(value, pathlib.Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize *value* as stable UTF-8 JSON bytes."""
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """SHA-256 of the canonical JSON representation of *value*."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    """SHA-256 of a file's exact bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
