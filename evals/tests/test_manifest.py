"""Tests for evals/datasets/v1/manifest.json integrity."""

from __future__ import annotations

import hashlib
import pathlib

from evals.schema import DatasetManifest, DocumentManifestEntry
from evals.tests.conftest import (
    EXPECTED_DOC_TYPES,
    EXPECTED_FILENAMES,
    EXPECTED_PAGE_COUNTS,
    SUPPORT_EBOOKS,
    TOTAL_ITEMS,
)


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestManifestStructure:
    def test_manifest_parses_as_dataset_manifest(self, manifest_data: dict) -> None:
        manifest = DatasetManifest(**manifest_data)
        assert manifest.version == "v1"

    def test_status_is_draft(self, manifest_data: dict) -> None:
        assert manifest_data["status"] == "draft"

    def test_spec_reference_present(self, manifest_data: dict) -> None:
        assert "7.3" in manifest_data.get("spec_reference", "")

    def test_attested_on_date(self, manifest_data: dict) -> None:
        assert manifest_data.get("attested_on") == "2026-08-03"

    def test_item_count_at_least_120(self, manifest_data: dict) -> None:
        assert manifest_data["item_count"] >= TOTAL_ITEMS

    def test_composition_keys(self, manifest_data: dict) -> None:
        comp = manifest_data["composition"]
        assert set(comp.keys()) == {"answerable", "unanswerable", "ambiguous_partial"}

    def test_composition_totals_match_item_count(self, manifest_data: dict) -> None:
        comp = manifest_data["composition"]
        assert sum(comp.values()) == manifest_data["item_count"]

    def test_composition_exact_counts(self, manifest_data: dict) -> None:
        comp = manifest_data["composition"]
        assert comp["answerable"] == 72
        assert comp["unanswerable"] == 30
        assert comp["ambiguous_partial"] == 18


class TestManifestDocuments:
    def test_exactly_six_documents(self, manifest_data: dict) -> None:
        assert len(manifest_data["documents"]) == 6

    def test_all_expected_filenames_present(self, manifest_data: dict) -> None:
        filenames = {d["filename"] for d in manifest_data["documents"]}
        assert filenames == EXPECTED_FILENAMES

    def test_doc_types_correct(self, manifest_data: dict) -> None:
        for doc in manifest_data["documents"]:
            expected = EXPECTED_DOC_TYPES[doc["filename"]]
            assert doc["doc_type"] == expected, (
                f"{doc['filename']}: expected {expected}, got {doc['doc_type']}"
            )

    def test_page_counts_correct(self, manifest_data: dict) -> None:
        for doc in manifest_data["documents"]:
            expected = EXPECTED_PAGE_COUNTS[doc["filename"]]
            assert doc["page_count"] == expected, (
                f"{doc['filename']}: expected {expected} pages, got {doc['page_count']}"
            )

    def test_sha256_matches_actual_files(self, manifest_data: dict) -> None:
        """Verify stored hashes match the actual PDF files (no network required)."""
        for doc in manifest_data["documents"]:
            pdf_path = SUPPORT_EBOOKS / doc["filename"]
            assert pdf_path.exists(), f"PDF not found: {pdf_path}"
            actual_hash = _sha256(pdf_path)
            assert doc["sha256"] == actual_hash, (
                f"{doc['filename']}: hash mismatch. Expected {doc['sha256']}, got {actual_hash}"
            )

    def test_license_basis_is_user_attestation(self, manifest_data: dict) -> None:
        for doc in manifest_data["documents"]:
            assert doc["license_basis"] == "user_attestation", (
                f"{doc['filename']}: license_basis must be 'user_attestation', "
                f"not '{doc['license_basis']}'"
            )

    def test_user_attestation_mentions_date(self, manifest_data: dict) -> None:
        for doc in manifest_data["documents"]:
            attestation = doc["user_attestation"]
            assert "2026-08-03" in attestation, (
                f"{doc['filename']}: user_attestation must reference attestation date"
            )

    def test_not_falsely_labeled_cc_or_public_domain(self, manifest_data: dict) -> None:
        """Ensure no doc is falsely labeled as CC or public domain."""
        forbidden = {"cc", "creative_commons", "public_domain", "cc0"}
        for doc in manifest_data["documents"]:
            basis = doc["license_basis"].lower()
            assert basis not in forbidden, (
                f"{doc['filename']}: license_basis '{basis}' is not permitted — "
                "do not falsely label user-attested content as CC/public-domain"
            )

    def test_provenance_paths_point_to_ebooks(self, manifest_data: dict) -> None:
        for doc in manifest_data["documents"]:
            assert "support/ebooks" in doc["provenance"].replace("\\", "/")

    def test_entries_parse_as_document_manifest_entry(self, manifest_data: dict) -> None:
        for doc_data in manifest_data["documents"]:
            DocumentManifestEntry(**doc_data)
