"""
review_artifact.py — Offline human-review artifact generator.

Produces a **self-contained** review surface (standalone HTML and/or CSV) that
lets a curator inspect every golden item — question, reference answer, evidence
quotes, source document and page(s) — and *record* a review decision, all
without running a web server.

Important
---------
This tool is read-only with respect to the dataset: it never edits
``golden.jsonl`` and never advances ``review_status``.  Every item is emitted
with its current status (``draft``).  The HTML captures a reviewer's decisions
in the browser (``localStorage``) and lets them export a CSV/JSON of decisions;
applying those decisions back to the dataset remains a deliberate, separate,
human-driven step.

For poor-scan fixtures the source page shown is the *original* source page
(resolved through the manifest ``page_map``) so the reviewer can locate the text
that grounds each quote, while the fixture page actually referenced by the item
is shown alongside.

Usage
-----
    python evals/review_artifact.py \\
        --dataset evals/datasets/v1/golden.jsonl \\
        --manifest evals/datasets/v1/manifest.json \\
        --output evals/datasets/v1/review \\
        --format both

``--format`` is one of ``html`` (default), ``csv`` or ``both``.  The output path
is used as a stem: ``<output>.html`` and/or ``<output>.csv`` are written.  The
output bytes are deterministic (no timestamps).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import pathlib
import sys

_REVIEW_STATES = ["draft", "reviewed_ok", "reviewed_changes_requested", "rejected"]


def _load_jsonl(path: pathlib.Path) -> list[dict]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def _load_manifest(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_page(doc: dict | None, page: int) -> int:
    if not doc:
        return page
    page_map = doc.get("page_map")
    if not page_map:
        return page
    return page_map.get(str(page), page)


def build_rows(items: list[dict], manifest: dict) -> list[dict]:
    """Flatten items into review rows with resolved source page references."""
    docs = {d["filename"]: d for d in manifest.get("documents", [])}
    rows: list[dict] = []
    for item in items:
        doc = docs.get(item.get("documento", ""))
        pages = item.get("paginas_esperadas") or []
        source_pages = [_source_page(doc, p) for p in pages]
        rows.append(
            {
                "id": item.get("id", ""),
                "tipo": item.get("tipo", ""),
                "dificuldade": item.get("dificuldade", ""),
                "documento": item.get("documento", ""),
                "corpus_path": (doc or {}).get("corpus_path", ""),
                "paginas_fixture": pages,
                "paginas_fonte": source_pages,
                "pergunta": item.get("pergunta", ""),
                "resposta_referencia": item.get("resposta_referencia") or "",
                "evidence_quotes": item.get("evidence_quotes") or [],
                "notas": item.get("notas") or "",
                "review_status": item.get("review_status", "draft"),
            }
        )
    return rows


def render_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "id",
            "tipo",
            "dificuldade",
            "documento",
            "corpus_path",
            "paginas_fixture",
            "paginas_fonte",
            "pergunta",
            "resposta_referencia",
            "evidence_quotes",
            "notas",
            "review_status_atual",
            "decisao_do_revisor",
            "comentario_do_revisor",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r["id"],
                r["tipo"],
                r["dificuldade"],
                r["documento"],
                r["corpus_path"],
                "; ".join(str(p) for p in r["paginas_fixture"]),
                "; ".join(str(p) for p in r["paginas_fonte"]),
                r["pergunta"],
                r["resposta_referencia"],
                " || ".join(r["evidence_quotes"]),
                r["notas"],
                r["review_status"],
                "",
                "",
            ]
        )
    return buffer.getvalue()


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Marco 3.5 — Revisão do corpus golden</title>
<style>
 body {{ font-family: system-ui, Arial, sans-serif; margin: 1.5rem; color: #1b1b1b; }}
 h1 {{ font-size: 1.3rem; }}
 .meta {{ color: #555; font-size: .85rem; margin-bottom: 1rem; }}
 .controls {{ margin: 1rem 0; }}
 .item {{ border: 1px solid #ccc; border-radius: 8px; padding: 1rem; margin: 1rem 0; }}
 .item h2 {{ font-size: 1rem; margin: 0 0 .3rem 0; }}
 .tags span {{ display: inline-block; background: #eef; border-radius: 4px;
   padding: 1px 6px; margin-right: 4px; font-size: .75rem; }}
 .q {{ font-weight: 600; margin: .4rem 0; }}
 .a {{ margin: .3rem 0; }}
 .quote {{ background: #f6f6f2; border-left: 3px solid #b9a; padding: .3rem .6rem;
   margin: .3rem 0; font-style: italic; }}
 .src {{ font-size: .8rem; color: #444; }}
 .notas {{ font-size: .85rem; color: #663; }}
 label {{ font-size: .85rem; }}
 select, textarea {{ font-family: inherit; }}
 textarea {{ width: 100%; min-height: 2.2rem; }}
 button {{ padding: .4rem .8rem; cursor: pointer; }}
 .u {{ color: #a00; }}
</style>
</head>
<body>
<h1>Marco 3.5 — Revisão do corpus golden</h1>
<div class="meta">
 {count} itens. Nenhum item é marcado como revisado por esta ferramenta — todos
 permanecem <code>review_status=draft</code>. Suas decisões ficam apenas no
 navegador até você exportá-las.
</div>
<div class="controls">
 <button onclick="exportJson()">Exportar decisões (JSON)</button>
 <button onclick="exportCsv()">Exportar decisões (CSV)</button>
 <button onclick="clearAll()">Limpar decisões locais</button>
</div>
<div id="items"></div>
<script>
const ITEMS = {data};
const STATES = {states};
const KEY = "marco35-review-decisions";
function load() {{ try {{ return JSON.parse(localStorage.getItem(KEY)) || {{}}; }}
  catch (e) {{ return {{}}; }} }}
function save(d) {{ localStorage.setItem(KEY, JSON.stringify(d)); }}
function esc(s) {{ const d = document.createElement("div"); d.textContent = s == null ? "" : s;
  return d.innerHTML; }}
function render() {{
  const decisions = load();
  const root = document.getElementById("items");
  root.innerHTML = "";
  ITEMS.forEach(function(it) {{
    const dec = decisions[it.id] || {{ decision: "draft", comment: "" }};
    const el = document.createElement("div");
    el.className = "item";
    let quotes = it.evidence_quotes.map(function(q) {{
      return '<div class="quote">' + esc(q) + '</div>'; }}).join("");
    let src = "";
    if (it.paginas_fixture.length) {{
      src = '<div class="src">Fonte: ' + esc(it.documento) +
        ' — páginas (item): ' + it.paginas_fixture.join(", ") +
        ' — páginas na fonte de texto: ' + it.paginas_fonte.join(", ") +
        ' (' + esc(it.corpus_path) + ')</div>';
    }} else {{
      src = '<div class="src u">Não respondível — sem páginas/evidência.</div>';
    }}
    let opts = STATES.map(function(s) {{
      return '<option value="' + s + '"' + (s === dec.decision ? " selected" : "") +
        '>' + s + '</option>'; }}).join("");
    el.innerHTML =
      '<h2>' + esc(it.id) + '</h2>' +
      '<div class="tags"><span>' + esc(it.tipo) + '</span><span>' +
        esc(it.dificuldade) + '</span><span>status atual: ' +
        esc(it.review_status) + '</span></div>' +
      '<div class="q">' + esc(it.pergunta) + '</div>' +
      (it.resposta_referencia ?
        '<div class="a"><b>Resposta de referência:</b> ' +
        esc(it.resposta_referencia) + '</div>' : "") +
      quotes + src +
      (it.notas ? '<div class="notas"><b>Notas:</b> ' + esc(it.notas) + '</div>' : "") +
      '<div style="margin-top:.5rem"><label>Decisão do revisor: ' +
        '<select data-id="' + esc(it.id) + '" class="dec">' + opts + '</select>' +
        '</label></div>' +
      '<textarea data-id="' + esc(it.id) + '" class="cmt" ' +
        'placeholder="Comentário do revisor">' + esc(dec.comment) + '</textarea>';
    root.appendChild(el);
  }});
  root.querySelectorAll("select.dec").forEach(function(sel) {{
    sel.addEventListener("change", function() {{
      const d = load(); const id = sel.getAttribute("data-id");
      d[id] = d[id] || {{}}; d[id].decision = sel.value; save(d);
    }});
  }});
  root.querySelectorAll("textarea.cmt").forEach(function(t) {{
    t.addEventListener("input", function() {{
      const d = load(); const id = t.getAttribute("data-id");
      d[id] = d[id] || {{}}; d[id].comment = t.value; save(d);
    }});
  }});
}}
function download(name, text, mime) {{
  const blob = new Blob([text], {{ type: mime }});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = name; a.click();
  URL.revokeObjectURL(a.href);
}}
function exportJson() {{ download("review-decisions.json",
  JSON.stringify(load(), null, 2), "application/json"); }}
function exportCsv() {{
  const d = load();
  let rows = [["id", "decisao_do_revisor", "comentario_do_revisor"]];
  ITEMS.forEach(function(it) {{
    const dec = d[it.id] || {{ decision: "draft", comment: "" }};
    rows.push([it.id, dec.decision || "draft", (dec.comment || "").replace(/\\n/g, " ")]);
  }});
  const csv = rows.map(function(r) {{
    return r.map(function(c) {{ return '"' + String(c).replace(/"/g, '""') + '"'; }}).join(",");
  }}).join("\\n");
  download("review-decisions.csv", csv, "text/csv");
}}
function clearAll() {{ if (confirm("Limpar todas as decisões locais?"))
  {{ localStorage.removeItem(KEY); render(); }} }}
render();
</script>
</body>
</html>
"""


def render_html(rows: list[dict]) -> str:
    data = json.dumps(rows, ensure_ascii=False)
    return _HTML_TEMPLATE.format(
        count=len(rows),
        data=data,
        states=json.dumps(_REVIEW_STATES),
    )


def generate(
    dataset_path: pathlib.Path,
    manifest_path: pathlib.Path,
    output_stem: pathlib.Path,
    fmt: str,
) -> list[pathlib.Path]:
    items = _load_jsonl(dataset_path)
    manifest = _load_manifest(manifest_path)
    rows = build_rows(items, manifest)

    written: list[pathlib.Path] = []
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    if fmt in ("html", "both"):
        html_path = output_stem.with_suffix(".html")
        html_path.write_text(render_html(rows), encoding="utf-8")
        written.append(html_path)
    if fmt in ("csv", "both"):
        csv_path = output_stem.with_suffix(".csv")
        csv_path.write_text(render_csv(rows), encoding="utf-8")
        written.append(csv_path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an offline review artifact.")
    parser.add_argument("--dataset", required=True, help="Path to golden.jsonl")
    parser.add_argument("--manifest", required=True, help="Path to manifest.json")
    parser.add_argument(
        "--output",
        required=True,
        help="Output path stem (extension is added per format).",
    )
    parser.add_argument(
        "--format",
        choices=["html", "csv", "both"],
        default="html",
        help="Artifact format(s) to write (default: html).",
    )
    args = parser.parse_args(argv)

    dataset_path = pathlib.Path(args.dataset)
    manifest_path = pathlib.Path(args.manifest)
    if not dataset_path.exists():
        print(f"ERROR: dataset not found: {dataset_path}", file=sys.stderr)
        return 1
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    written = generate(
        dataset_path,
        manifest_path,
        pathlib.Path(args.output),
        args.format,
    )
    for path in written:
        print(f"Review artifact written: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
