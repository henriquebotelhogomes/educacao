"""Test configuration that prevents network telemetry exports."""

import os

os.environ["MENTORA_TELEMETRY_ENABLED"] = "false"
os.environ["MENTORA_JWT_SECRET"] = "test-secret-not-for-production-with-at-least-32-bytes"
os.environ["MENTORA_MINIO_ACCESS_KEY"] = "minioadmin"
os.environ["MENTORA_MINIO_SECRET_KEY"] = "minioadmin_dev_only"
