from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from _common import now_iso, read_json, render_pdf, sha256_file, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create full-page source/output comparison sheets.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-pdf", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--renderer", required=True)
    parser.add_argument("--dpi", type=int, default=150)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "comparison-index.json"
    try:
        manifest = read_json(args.manifest.resolve())
        source_pages = manifest.get("pages")
        if not isinstance(source_pages, list) or not source_pages:
            raise ValueError("Manifest contains no source pages.")
        rendered = render_pdf(args.output_pdf.resolve(), output_dir / "rendered-output-page", args.renderer, args.dpi)
        if rendered["status"] != "PASS":
            raise ValueError(f"Unable to render output PDF: {rendered.get('stderr', '')}")
        output_pages = [Path(path) for path in rendered["pages"]]
        if len(source_pages) != len(output_pages):
            raise ValueError(f"Page count mismatch: source {len(source_pages)}, output {len(output_pages)}.")

        records: list[dict[str, object]] = []
        for index, (source_record, output_page) in enumerate(zip(source_pages, output_pages), start=1):
            source_path = Path(str(source_record["derived_page_path"]))
            if not source_path.is_absolute():
                source_path = args.manifest.resolve().parent / source_path
            with Image.open(source_path) as source_opened, Image.open(output_page) as output_opened:
                source = source_opened.convert("RGB")
                output = output_opened.convert("RGB")
            target_height = max(source.height, output.height)
            source_scaled = ImageOps.contain(source, (max(source.width, output.width), target_height))
            output_scaled = ImageOps.contain(output, (max(source.width, output.width), target_height))
            gutter = 24
            header = 42
            sheet = Image.new(
                "RGB",
                (source_scaled.width + output_scaled.width + gutter, max(source_scaled.height, output_scaled.height) + header),
                "white",
            )
            draw = ImageDraw.Draw(sheet)
            draw.text((8, 10), f"SOURCE p{index:03d}", fill="black")
            draw.text((source_scaled.width + gutter + 8, 10), f"OUTPUT p{index:03d}", fill="black")
            sheet.paste(source_scaled, (0, header))
            sheet.paste(output_scaled, (source_scaled.width + gutter, header))
            comparison = output_dir / f"page-{index:04d}-side-by-side.png"
            sheet.save(comparison, format="PNG")
            records.append(
                {
                    "page_id": source_record.get("page_id", f"p{index:03d}"),
                    "source_page": str(source_path.resolve()),
                    "output_render": str(output_page.resolve()),
                    "comparison": str(comparison.resolve()),
                    "comparison_sha256": sha256_file(comparison),
                }
            )
        result = {
            "status": "PASS",
            "created_at": now_iso(),
            "source_manifest": str(args.manifest.resolve()),
            "output_pdf": str(args.output_pdf.resolve()),
            "page_count": len(records),
            "pages": records,
        }
        write_json(index_path, result)
        print(str(index_path))
        return 0
    except Exception as exc:
        write_json(index_path, {"status": "FAIL", "created_at": now_iso(), "page_count": 0, "pages": [], "error": str(exc)})
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
