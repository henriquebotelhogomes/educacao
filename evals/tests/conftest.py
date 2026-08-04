"""Shared test fixtures for evals tests."""

from __future__ import annotations

import json
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
EVALS_ROOT = REPO_ROOT / "evals"
DATASETS_V1 = EVALS_ROOT / "datasets" / "v1"
SUPPORT_EBOOKS = REPO_ROOT / "support" / "ebooks"
FIXTURES_DIR = EVALS_ROOT / "fixtures"

MANIFEST_PATH = DATASETS_V1 / "manifest.json"
GOLDEN_PATH = DATASETS_V1 / "golden.jsonl"

# The poor-scan logical document is the derived, image-only fixture — NOT the
# original text PDF.  Its corpus_path still points at the original text source so
# the evidence audit can read real page text.
POOR_SCAN_FILENAME = "ph-gerente-editora-cerrado-goiano-poor-scan.pdf"
POOR_SCAN_SOURCE_FILENAME = "ph,+Gerente+da+editora,+cerrado-goiano.pdf"
FIXTURE_PATH = FIXTURES_DIR / POOR_SCAN_FILENAME
POOR_SCAN_SOURCE_PATH = SUPPORT_EBOOKS / POOR_SCAN_SOURCE_FILENAME

EXPECTED_FILENAMES = {
    "História Agrária.pdf",
    "historia-das-agriculturas-no-mundo-mazoyer-e-roudart.pdf",
    "Políticas-públicas-agricultura-familiar-e-sustentabilidade.pdf",
    "buhler-9786557250044.pdf",
    "LIVRO  MUNDIALIZAÇÃO pronto.pdf",
    POOR_SCAN_FILENAME,
}

EXPECTED_DOC_TYPES = {
    "História Agrária.pdf": "narrative",
    "historia-das-agriculturas-no-mundo-mazoyer-e-roudart.pdf": "narrative",
    "Políticas-públicas-agricultura-familiar-e-sustentabilidade.pdf": "table_heavy",
    "buhler-9786557250044.pdf": "table_heavy",
    "LIVRO  MUNDIALIZAÇÃO pronto.pdf": "dense",
    POOR_SCAN_FILENAME: "poor_scan",
}

EXPECTED_PAGE_COUNTS = {
    "buhler-9786557250044.pdf": 277,
    "historia-das-agriculturas-no-mundo-mazoyer-e-roudart.pdf": 569,
    "História Agrária.pdf": 315,
    "LIVRO  MUNDIALIZAÇÃO pronto.pdf": 545,
    POOR_SCAN_FILENAME: 18,
    "Políticas-públicas-agricultura-familiar-e-sustentabilidade.pdf": 214,
}

# The five text documents live under support/ebooks and are their own corpus.
# The poor-scan fixture's corpus is the original text source.
EXPECTED_CORPUS_PATHS = {
    "História Agrária.pdf": "support/ebooks/História Agrária.pdf",
    "historia-das-agriculturas-no-mundo-mazoyer-e-roudart.pdf": (
        "support/ebooks/historia-das-agriculturas-no-mundo-mazoyer-e-roudart.pdf"
    ),
    "Políticas-públicas-agricultura-familiar-e-sustentabilidade.pdf": (
        "support/ebooks/Políticas-públicas-agricultura-familiar-e-sustentabilidade.pdf"
    ),
    "buhler-9786557250044.pdf": "support/ebooks/buhler-9786557250044.pdf",
    "LIVRO  MUNDIALIZAÇÃO pronto.pdf": "support/ebooks/LIVRO  MUNDIALIZAÇÃO pronto.pdf",
    POOR_SCAN_FILENAME: f"support/ebooks/{POOR_SCAN_SOURCE_FILENAME}",
}

TOTAL_ITEMS = 120
EXPECTED_ANSWERABLE = 72
EXPECTED_UNANSWERABLE = 30
EXPECTED_AMBIGUOUS_PARTIAL = 18
ITEMS_PER_DOC = 20


@pytest.fixture(scope="session")
def manifest_data() -> dict:
    assert MANIFEST_PATH.exists(), f"Manifest not found: {MANIFEST_PATH}"
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def golden_items() -> list[dict]:
    assert GOLDEN_PATH.exists(), f"Golden dataset not found: {GOLDEN_PATH}"
    items = []
    for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items
