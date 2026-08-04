"""
generate_degraded_fixture.py — Deterministic poor-scan fixture generator.

Renders a fixed set of representative pages from the ``cerrado-goiano`` source
PDF to raster with ``pypdfium2``, applies deterministic scan degradation
(grayscale, contrast loss, Gaussian blur, additive noise and a slight skew) with
Pillow, and assembles the result into an **image-only** multipage PDF.

Because the output PDF carries no text layer, text extraction from it is empty;
the raster pages, however, still visibly contain the source content.  The
mapping from fixture page → original source page is written to the provenance
JSON so evidence can be audited against the original text.

Usage
-----
    python evals/generate_degraded_fixture.py \\
        --source "support/ebooks/ph,+Gerente+da+editora,+cerrado-goiano.pdf" \\
        --output evals/fixtures \\
        --seed 42

By default the canonical :data:`REPRESENTATIVE_PAGES` are used so the committed
fixture is reproducible.  Pass ``--pages`` to override.

Outputs
-------
    evals/fixtures/ph-gerente-editora-cerrado-goiano-poor-scan.pdf  (image-only)
    evals/fixtures/fixture_provenance.json                          (page map)

Reproducibility guarantee
-------------------------
Given identical ``--source``, ``--pages``, ``--seed``, ``--dpi`` and
``--quality`` the output bytes are identical: rendering, degradation and JPEG
encoding are all deterministic and the PDF is assembled without timestamps.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import random
import sys

# Canonical representative source pages (1-indexed) rendered into the fixture,
# in order.  Each has substantial extractable text in the original so that the
# 15 non-unanswerable poor-scan golden items reference real, grounded pages.
REPRESENTATIVE_PAGES: tuple[int, ...] = (
    18,
    20,
    22,
    24,
    26,
    28,
    30,
    32,
    40,
    45,
    50,
    55,
    60,
    65,
    70,
    75,
    80,
    85,
)

DEFAULT_FIXTURE_NAME = "ph-gerente-editora-cerrado-goiano-poor-scan.pdf"


def _sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_source_pages(
    source_pdf: pathlib.Path,
    pages: list[int],
    dpi: int,
):
    """Render 1-indexed ``pages`` of ``source_pdf`` to Pillow images at ``dpi``."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(source_pdf))
    try:
        scale = dpi / 72.0
        rendered = []
        n = len(document)
        for page_no in pages:
            if not (1 <= page_no <= n):
                raise ValueError(f"page {page_no} out of range (source has {n} pages)")
            page = document[page_no - 1]
            bitmap = page.render(scale=scale)
            rendered.append(bitmap.to_pil().convert("L"))
            bitmap.close()
            page.close()
        return rendered
    finally:
        document.close()


def degrade_image(image, seed: int):
    """Apply deterministic scan degradation to a grayscale Pillow image.

    Steps: contrast loss → Gaussian blur → additive per-pixel noise → slight
    skew.  Fully determined by ``seed`` and the input pixels.
    """
    from PIL import Image, ImageEnhance, ImageFilter

    gray = image.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(0.62)
    gray = ImageEnhance.Brightness(gray).enhance(1.06)
    gray = gray.filter(ImageFilter.GaussianBlur(radius=1.1))

    width, height = gray.size
    rng = random.Random(seed)
    noise = Image.frombytes("L", (width, height), rng.randbytes(width * height))
    gray = Image.blend(gray, noise, alpha=0.14)

    # Slight, deterministic skew simulating a misaligned scan.
    angle = 0.6 if (seed % 2 == 0) else -0.6
    gray = gray.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False, fillcolor=246)
    return gray


def _encode_jpeg(image, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.convert("L").save(buffer, format="JPEG", quality=quality, optimize=False)
    return buffer.getvalue()


def write_image_only_pdf(images, out_path: pathlib.Path, quality: int = 40) -> None:
    """Assemble ``images`` into a deterministic, image-only (no text) PDF.

    Each page embeds one grayscale JPEG via ``DCTDecode``.  The writer emits no
    timestamps or producer metadata, so identical inputs yield identical bytes.
    """
    objects: list[bytes] = []

    def add_object(body: bytes) -> int:
        objects.append(body)
        return len(objects)  # 1-indexed object number

    catalog_num = add_object(b"")  # 1 — filled after Pages known
    pages_num = add_object(b"")  # 2 — filled after kids known

    kids: list[int] = []
    for image in images:
        jpeg = _encode_jpeg(image, quality)
        width, height = image.size
        image_num = add_object(
            (
                f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
                f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /DCTDecode "
                f"/Length {len(jpeg)} >>\nstream\n"
            ).encode("latin-1")
            + jpeg
            + b"\nendstream"
        )
        content = f"q {width} 0 0 {height} 0 0 cm /Im0 Do Q".encode("latin-1")
        content_num = add_object(
            (f"<< /Length {len(content)} >>\nstream\n").encode("latin-1") + content + b"\nendstream"
        )
        page_num = add_object(
            (
                f"<< /Type /Page /Parent {pages_num} 0 R "
                f"/MediaBox [0 0 {width} {height}] "
                f"/Resources << /XObject << /Im0 {image_num} 0 R >> >> "
                f"/Contents {content_num} 0 R >>"
            ).encode("latin-1")
        )
        kids.append(page_num)

    objects[catalog_num - 1] = f"<< /Type /Catalog /Pages {pages_num} 0 R >>".encode("latin-1")
    kids_str = " ".join(f"{k} 0 R" for k in kids)
    objects[pages_num - 1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(kids)} >>".encode(
        "latin-1"
    )

    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode("latin-1") + body + b"\nendobj\n"

    xref_pos = len(out)
    count = len(objects) + 1
    out += f"xref\n0 {count}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {count} /Root {catalog_num} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode("latin-1")

    out_path.write_bytes(bytes(out))


def generate_degraded_fixture(
    source_pdf: pathlib.Path,
    output_dir: pathlib.Path,
    pages: list[int] | None = None,
    seed: int = 42,
    dpi: int = 110,
    quality: int = 20,
    fixture_name: str = DEFAULT_FIXTURE_NAME,
) -> pathlib.Path:
    """Render, degrade and assemble the image-only poor-scan fixture.

    Returns the path to the written fixture PDF and writes a provenance JSON
    (with the fixture-page → source-page map) alongside it.  ``dpi`` and
    ``quality`` are kept modest so the committed fixture stays small while the
    raster pages remain legible enough to visibly carry the source content.
    """
    source_pdf = pathlib.Path(source_pdf)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = list(pages) if pages is not None else list(REPRESENTATIVE_PAGES)

    rendered = render_source_pages(source_pdf, selected, dpi=dpi)
    degraded = [degrade_image(img, seed=seed + idx) for idx, img in enumerate(rendered)]

    fixture_path = output_dir / fixture_name
    write_image_only_pdf(degraded, fixture_path, quality=quality)

    source_hash = _sha256_file(source_pdf)
    page_map = {str(i + 1): src for i, src in enumerate(selected)}
    provenance = {
        "fixture_pdf": fixture_path.name,
        "fixture_sha256": _sha256_file(fixture_path),
        "fixture_page_count": len(selected),
        "source_pdf": str(source_pdf).replace("\\", "/"),
        "source_sha256": source_hash,
        "page_map": page_map,
        "seed": seed,
        "dpi": dpi,
        "quality": quality,
        "generator": "evals/generate_degraded_fixture.py",
        "degradation": "grayscale, contrast loss, Gaussian blur, additive noise, skew",
        "notes": (
            "Image-only fixture: text extraction from this PDF is empty by "
            "construction. Fixture page N maps to the original source page given "
            "in page_map. The source PDF is authorized for use per user "
            "attestation on 2026-08-03; any embedded copyright notices are "
            "preserved and take precedence."
        ),
    }
    prov_path = output_dir / "fixture_provenance.json"
    prov_path.write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    return fixture_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic image-only poor-scan fixture.",
    )
    parser.add_argument("--source", required=True, help="Path to source PDF (cerrado-goiano).")
    parser.add_argument("--output", default="evals/fixtures", help="Output directory.")
    parser.add_argument(
        "--pages",
        type=int,
        nargs="*",
        default=None,
        help="1-indexed source pages to render (default: canonical representative set).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Degradation seed (default: 42).")
    parser.add_argument("--dpi", type=int, default=110, help="Render DPI (default: 110).")
    parser.add_argument(
        "--quality", type=int, default=20, help="JPEG quality for pages (default: 20)."
    )

    args = parser.parse_args(argv)
    source = pathlib.Path(args.source)
    if not source.exists():
        print(f"ERROR: source PDF not found: {source}", file=sys.stderr)
        return 1

    fixture = generate_degraded_fixture(
        source_pdf=source,
        output_dir=pathlib.Path(args.output),
        pages=args.pages,
        seed=args.seed,
        dpi=args.dpi,
        quality=args.quality,
    )
    print(f"Fixture PDF written:      {fixture}")
    print(f"Provenance JSON written:  {pathlib.Path(args.output) / 'fixture_provenance.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
