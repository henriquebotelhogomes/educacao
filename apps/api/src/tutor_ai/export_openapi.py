"""Export the FastAPI contract for TypeScript generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tutor_ai.main import app


def main() -> None:
    output_path = Path(sys.argv[1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
