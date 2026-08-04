"""Tests for the validate CLI (evals/validate.py)."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

from evals.tests.conftest import EVALS_ROOT, GOLDEN_PATH, MANIFEST_PATH


def _sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestValidateCLICheck:
    def test_check_exits_zero_on_valid_dataset(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(EVALS_ROOT / "validate.py"),
                "check",
                "--dataset",
                str(GOLDEN_PATH),
                "--manifest",
                str(MANIFEST_PATH),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"validate check failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_check_reports_item_count(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(EVALS_ROOT / "validate.py"),
                "check",
                "--dataset",
                str(GOLDEN_PATH),
                "--manifest",
                str(MANIFEST_PATH),
            ],
            capture_output=True,
            text=True,
        )
        assert "120" in result.stdout or "120" in result.stderr

    def test_check_fails_on_missing_dataset(self, tmp_path: pathlib.Path) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(EVALS_ROOT / "validate.py"),
                "check",
                "--dataset",
                str(tmp_path / "nonexistent.jsonl"),
                "--manifest",
                str(MANIFEST_PATH),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0


class TestValidateCLIFreeze:
    def test_freeze_creates_lock_file(self, tmp_path: pathlib.Path) -> None:
        lock_path = tmp_path / "lock.json"
        result = subprocess.run(
            [
                sys.executable,
                str(EVALS_ROOT / "validate.py"),
                "freeze",
                "--dataset",
                str(GOLDEN_PATH),
                "--manifest",
                str(MANIFEST_PATH),
                "--output",
                str(lock_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"freeze failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert lock_path.exists()

    def test_lock_file_contains_correct_sha256(self, tmp_path: pathlib.Path) -> None:
        lock_path = tmp_path / "lock.json"
        subprocess.run(
            [
                sys.executable,
                str(EVALS_ROOT / "validate.py"),
                "freeze",
                "--dataset",
                str(GOLDEN_PATH),
                "--manifest",
                str(MANIFEST_PATH),
                "--output",
                str(lock_path),
            ],
            check=True,
            capture_output=True,
        )
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        expected_dataset_hash = _sha256_file(GOLDEN_PATH)
        assert lock["dataset_sha256"] == expected_dataset_hash

    def test_lock_file_has_correct_composition(self, tmp_path: pathlib.Path) -> None:
        lock_path = tmp_path / "lock.json"
        subprocess.run(
            [
                sys.executable,
                str(EVALS_ROOT / "validate.py"),
                "freeze",
                "--dataset",
                str(GOLDEN_PATH),
                "--manifest",
                str(MANIFEST_PATH),
                "--output",
                str(lock_path),
            ],
            check=True,
            capture_output=True,
        )
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        assert lock["composition"]["answerable"] == 72
        assert lock["composition"]["unanswerable"] == 30
        assert lock["composition"]["ambiguous_partial"] == 18
        assert lock["item_count"] == 120

    def test_lock_parses_as_lock_manifest(self, tmp_path: pathlib.Path) -> None:
        from evals.schema import LockManifest

        lock_path = tmp_path / "lock.json"
        subprocess.run(
            [
                sys.executable,
                str(EVALS_ROOT / "validate.py"),
                "freeze",
                "--dataset",
                str(GOLDEN_PATH),
                "--manifest",
                str(MANIFEST_PATH),
                "--output",
                str(lock_path),
            ],
            check=True,
            capture_output=True,
        )
        lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
        LockManifest(**lock_data)
