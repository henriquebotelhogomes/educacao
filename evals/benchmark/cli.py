"""Command-line interface for the ADR-018 benchmark harness."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Mapping

from evals.benchmark.chunking_experiment import default_chunking_variants
from evals.benchmark.hashing import canonical_sha256, sha256_file
from evals.benchmark.publishability import effective_document_hashes
from evals.benchmark.registry import CANDIDATES
from evals.benchmark.report import (
    load_result_jsons,
    render_chunking_markdown_comparison,
    render_markdown_comparison,
)
from evals.benchmark.runner import (
    PublishabilityError,
    fake_smoke_result,
    make_config,
    run_benchmark,
    write_result_json,
)
from evals.benchmark.schemas import BenchmarkConfig

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DEFAULT_CACHE_DIR = _REPO_ROOT / "evals" / ".cache" / "benchmark"


def existing_result_matches_config(
    result: Mapping[str, object],
    *,
    config: BenchmarkConfig,
    dataset_path: pathlib.Path,
    manifest_path: pathlib.Path,
) -> bool:
    model = result.get("model")
    hashes = result.get("hashes")
    if not isinstance(model, Mapping) or not isinstance(hashes, Mapping):
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    document_hashes_sha256 = canonical_sha256(
        effective_document_hashes(manifest, repo_root=_REPO_ROOT)
    )
    return (
        model.get("model_name") == config.model_name
        and hashes.get("config_sha256") == canonical_sha256(config.deterministic_payload())
        and hashes.get("dataset_sha256") == sha256_file(dataset_path)
        and hashes.get("manifest_sha256") == sha256_file(manifest_path)
        and hashes.get("document_hashes_sha256") == document_hashes_sha256
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ADR-018 embedding benchmark harness")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run one embedding benchmark candidate or the full matrix")
    run.add_argument("--model", required=True, help="Candidate alias or 'all'")
    run.add_argument("--dataset", required=True, help="Path to golden.jsonl")
    run.add_argument("--manifest", required=True, help="Path to manifest.json")
    run.add_argument("--output", required=True, help="Result JSON path or output directory for all")
    run.add_argument("--device", default="cpu", help="SentenceTransformer device, e.g. cpu/cuda")
    run.add_argument("--offline", action="store_true", help="Use only locally cached HF models")
    run.add_argument(
        "--publish",
        action="store_true",
        help="Refuse unless publishability gate passes",
    )
    run.add_argument("--max-pages-per-document", type=int, default=None)
    run.add_argument("--max-items", type=int, default=None)
    run.add_argument("--cache-dir", default=str(_DEFAULT_CACHE_DIR))

    chunking = sub.add_parser("chunking", help="Run the ADR-012 chunking strategy matrix")
    chunking.add_argument("--model", required=True, help="One embedding candidate alias")
    chunking.add_argument("--dataset", required=True, help="Path to golden.jsonl")
    chunking.add_argument("--manifest", required=True, help="Path to manifest.json")
    chunking.add_argument("--output", required=True, help="Output directory")
    chunking.add_argument("--device", default="cpu")
    chunking.add_argument("--offline", action="store_true")
    chunking.add_argument("--publish", action="store_true")
    chunking.add_argument("--max-pages-per-document", type=int, default=None)
    chunking.add_argument("--max-items", type=int, default=None)
    chunking.add_argument(
        "--strategy",
        choices=("structural", "semantic"),
        default=None,
        help="Run only one strategy",
    )
    chunking.add_argument(
        "--chunk-size",
        choices=(256, 512, 1024),
        type=int,
        default=None,
        help="Run only one target chunk size",
    )
    chunking.add_argument("--cache-dir", default=str(_DEFAULT_CACHE_DIR))

    smoke = sub.add_parser("smoke", help="Run a lightweight fake-embedder smoke benchmark")
    smoke.add_argument("--output", required=True, help="Path to write smoke result JSON")

    report = sub.add_parser("report", help="Render Markdown comparison from result JSON files")
    report.add_argument("--inputs", nargs="+", required=True, help="Result JSON paths")
    report.add_argument("--output", help="Optional Markdown output path")

    chunking_report = sub.add_parser(
        "chunking-report",
        help="Render an ADR-012 Markdown comparison",
    )
    chunking_report.add_argument("--inputs", nargs="+", required=True)
    chunking_report.add_argument("--output", help="Optional Markdown output path")
    return parser


def _resolve_output(output: pathlib.Path, alias: str, *, all_models: bool) -> pathlib.Path:
    if all_models:
        return output / f"{alias}.json"
    if output.suffix.lower() == ".json":
        return output
    return output / f"{alias}.json"


def _run(args: argparse.Namespace) -> int:
    aliases = list(CANDIDATES) if args.model == "all" else [args.model]
    unknown = [alias for alias in aliases if alias not in CANDIDATES]
    if unknown:
        print(f"ERROR: unknown model alias: {unknown[0]}", file=sys.stderr)
        return 2

    dataset = pathlib.Path(args.dataset)
    manifest = pathlib.Path(args.manifest)
    if not dataset.exists():
        print(f"ERROR: dataset not found: {dataset}", file=sys.stderr)
        return 1
    if not manifest.exists():
        print(f"ERROR: manifest not found: {manifest}", file=sys.stderr)
        return 1

    output = pathlib.Path(args.output)
    if args.model == "all" and output.suffix.lower() == ".json":
        print("ERROR: --output must be a directory when --model all", file=sys.stderr)
        return 2

    for alias in aliases:
        candidate = CANDIDATES[alias]
        output_path = _resolve_output(output, alias, all_models=args.model == "all")
        config = make_config(
            candidate=candidate,
            dataset_path=dataset,
            manifest_path=manifest,
            output_path=output_path,
            device=args.device,
            offline=bool(args.offline),
            max_pages_per_document=args.max_pages_per_document,
            max_items=args.max_items,
            publish_requested=bool(args.publish),
        )
        try:
            result = run_benchmark(
                config=config,
                candidate=candidate,
                repo_root=_REPO_ROOT,
                cache_dir=pathlib.Path(args.cache_dir),
            )
        except PublishabilityError as exc:
            print(f"ERROR: --publish refused: {exc}", file=sys.stderr)
            return 3
        write_result_json(result, output_path)
        print(f"Wrote {output_path}")
    return 0


def _smoke(args: argparse.Namespace) -> int:
    output = pathlib.Path(args.output)
    result = fake_smoke_result(output)
    write_result_json(result, output)
    print(f"Wrote {output}")
    return 0


def _chunking(args: argparse.Namespace) -> int:
    if args.model not in CANDIDATES:
        print(f"ERROR: unknown model alias: {args.model}", file=sys.stderr)
        return 2
    dataset = pathlib.Path(args.dataset)
    manifest = pathlib.Path(args.manifest)
    if not dataset.exists():
        print(f"ERROR: dataset not found: {dataset}", file=sys.stderr)
        return 1
    if not manifest.exists():
        print(f"ERROR: manifest not found: {manifest}", file=sys.stderr)
        return 1

    candidate = CANDIDATES[args.model]
    output_dir = pathlib.Path(args.output)
    variants = [
        variant
        for variant in default_chunking_variants()
        if (args.strategy is None or variant.strategy == args.strategy)
        and (args.chunk_size is None or variant.chunk_size == args.chunk_size)
    ]
    for variant in variants:
        output_path = output_dir / f"{variant.strategy_version}.json"
        config = make_config(
            candidate=candidate,
            dataset_path=dataset,
            manifest_path=manifest,
            output_path=output_path,
            device=args.device,
            offline=bool(args.offline),
            max_pages_per_document=args.max_pages_per_document,
            max_items=args.max_items,
            publish_requested=bool(args.publish),
            chunking_variant=variant,
        )
        if output_path.exists():
            try:
                existing = json.loads(output_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {}
            if existing_result_matches_config(
                existing,
                config=config,
                dataset_path=dataset,
                manifest_path=manifest,
            ):
                print(f"Skipped compatible existing result {output_path}")
                continue
            print(
                f"ERROR: incompatible existing result, refusing to overwrite: {output_path}",
                file=sys.stderr,
            )
            return 4
        try:
            result = run_benchmark(
                config=config,
                candidate=candidate,
                repo_root=_REPO_ROOT,
                cache_dir=pathlib.Path(args.cache_dir),
                chunking_variant=variant,
            )
        except PublishabilityError as exc:
            print(f"ERROR: --publish refused: {exc}", file=sys.stderr)
            return 3
        write_result_json(result, output_path)
        print(f"Wrote {output_path}")
    return 0


def _report(args: argparse.Namespace) -> int:
    inputs = [pathlib.Path(path) for path in args.inputs]
    missing = [path for path in inputs if not path.exists()]
    if missing:
        print(f"ERROR: result not found: {missing[0]}", file=sys.stderr)
        return 1
    markdown = render_markdown_comparison(load_result_jsons(inputs))
    if args.output:
        output = pathlib.Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
        print(f"Wrote {output}")
    else:
        print(markdown, end="")
    return 0


def _chunking_report(args: argparse.Namespace) -> int:
    inputs = [pathlib.Path(path) for path in args.inputs]
    missing = [path for path in inputs if not path.exists()]
    if missing:
        print(f"ERROR: result not found: {missing[0]}", file=sys.stderr)
        return 1
    markdown = render_chunking_markdown_comparison(load_result_jsons(inputs))
    if args.output:
        output = pathlib.Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
        print(f"Wrote {output}")
    else:
        print(markdown, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    if args.command == "run":
        return _run(args)
    if args.command == "chunking":
        return _chunking(args)
    if args.command == "smoke":
        return _smoke(args)
    if args.command == "report":
        return _report(args)
    if args.command == "chunking-report":
        return _chunking_report(args)
    parser.print_help()
    return 1
