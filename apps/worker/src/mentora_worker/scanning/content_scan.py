"""Content scanning per ADR-022: EICAR for dev/test, fail-closed outside dev."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Real EICAR test-file signature (single backslash before P in [4\PZX54).
_EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

_DEV_ENVS = frozenset({"development", "test"})


@dataclass
class ContentScanResult:
    """Result of a content scan."""

    clean: bool
    reason: str = field(default="")


class ContentScanner:
    """Scans document bytes for malicious content (ADR-022).

    In ``development`` / ``test`` environments an EICAR-signature check is used.
    In all other environments the scanner is fail-closed: no real AV engine is
    wired up, so any document is considered unsafe.  Swap this class out before
    moving to production.
    """

    def __init__(self, environment: str) -> None:
        self._environment = environment

    def scan(self, data: bytes) -> ContentScanResult:
        """Return a ContentScanResult for *data*."""
        if self._environment in _DEV_ENVS:
            return self._dev_scan(data)

        logger.error(
            "No production scanner configured (env=%s). "
            "Marking document as QUARANTINED. "
            "The dev EICAR scanner is NOT production-grade.",
            self._environment,
        )
        return ContentScanResult(clean=False, reason="no_scanner_configured")

    def _dev_scan(self, data: bytes) -> ContentScanResult:
        """EICAR-only scanner — development / test use only."""
        if _EICAR_SIGNATURE in data:
            return ContentScanResult(clean=False, reason="eicar_test_signature")
        logger.debug("Dev scan pass (NOT production-grade).")
        return ContentScanResult(clean=True)
