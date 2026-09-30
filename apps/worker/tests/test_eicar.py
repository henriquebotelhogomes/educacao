"""Tests for ContentScanner EICAR detection (ADR-022)."""

from __future__ import annotations

from mentora_worker.scanning.content_scan import (
    _EICAR_SIGNATURE,
    ContentScanner,
)

_CLEAN_BYTES = b"This is perfectly safe content with no malware."


def test_dev_scanner_detects_eicar() -> None:
    scanner = ContentScanner("development")
    result = scanner.scan(_EICAR_SIGNATURE)
    assert result.clean is False
    assert result.reason == "eicar_test_signature"


def test_dev_scanner_passes_clean_bytes() -> None:
    scanner = ContentScanner("development")
    result = scanner.scan(_CLEAN_BYTES)
    assert result.clean is True


def test_test_env_scanner_detects_eicar() -> None:
    scanner = ContentScanner("test")
    result = scanner.scan(_EICAR_SIGNATURE)
    assert result.clean is False
    assert result.reason == "eicar_test_signature"


def test_production_env_fails_closed() -> None:
    """Outside dev/test any input must be marked unsafe (no real scanner configured)."""
    scanner = ContentScanner("production")
    result = scanner.scan(_CLEAN_BYTES)
    assert result.clean is False
    assert result.reason == "no_scanner_configured"


def test_staging_env_fails_closed() -> None:
    scanner = ContentScanner("staging")
    result = scanner.scan(_CLEAN_BYTES)
    assert result.clean is False
