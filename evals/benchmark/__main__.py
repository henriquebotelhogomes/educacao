"""Module entry point for ``python -m evals.benchmark``."""

from __future__ import annotations

import sys

from evals.benchmark.cli import main

if __name__ == "__main__":
    sys.exit(main())
