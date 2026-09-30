"""Worker test configuration — forces test environment before any import."""

from __future__ import annotations

import os

os.environ["MENTORA_ENVIRONMENT"] = "test"
os.environ["MENTORA_MINIO_ACCESS_KEY"] = "minioadmin"
os.environ["MENTORA_MINIO_SECRET_KEY"] = "minioadmin_dev_only"
