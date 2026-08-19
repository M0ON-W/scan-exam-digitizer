from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

from _common import now_iso, read_json, render_pdf, resolve_executable, sha256_file, write_json


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze and inspect exam pages after a passing PRE-FLIGHT.")
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--job-dir", required=True, type=Path)
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--renderer", default="pdftoppm")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        preflight = read_json(args.preflight.resolve())
    except Exception as exc:
        print(f"Unable to read PRE-FLIGHT evidence: {exc}", file=sys.stderr)
        return 2
    if preflight.get("status") != "PASS":
        print("PRE-FLIGHT status is not PASS; page inspection is blocked.", file=sys.stderr)
        return 2
    if args.dpi <= 0:
        print("DPI must be positive.", file=sys.stderr)
        return 2

    job_dir = args.job_dir.resolve()
    pages_dir = job_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    audit_dir = job_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    renderer = resolve_executable(args.renderer)
    inputs = [path.resolve() for path in args.input]
    source_files: list[dict[str, object]] = []
    page_records: list[dict[str, object]] = []
    seen_hashes: dict[str, str] = {}
    page_number = 0

    try:
        for source_order, source in enumerate(inputs, start=1):
            if not source.exists() or not source.is_file():
                raise ValueError(f"Input not found: {source}")
            source_hash = sha256_file(source)
            source_files.append({"path": str(source), "sha256": source_hash, "input_order": source_order})
            derived_inputs: list[Path]
            temporary: tempfile.TemporaryDirectory[str] | None = None
            if source.suffix.lower() == ".pdf":
                if renderer is None:
                    raise ValueError("PDF input requires an available pdftoppm renderer.")
                temporary = tempfile.TemporaryDirectory()
                prefix = Path(temporary.name) / "source-page"
                rendered = render_pdf(source, prefix, renderer, dpi=args.dpi)
                if rendered["status"] != "PASS":
                    raise ValueError(f"Unable to render PDF input: {rendered.get('stderr', '')}")
                derived_inputs = [Path(path) for path in rendered["pages"]]
            elif source.suffix.lower() in IMAGE_SUFFIXES:
                derived_inputs = [source]
            else:
                raise ValueError(f"Unsupported input type: {source.suffix}")

            for source_page_index, derived_input in enumerate(derived_inputs, start=1):
                page_number += 1
                page_id = f"p{page_number:03d}"
                page_path = pages_dir / f"page-{page_number:04d}.png"
                with Image.open(derived_input) as opened:
                    image = opened.convert("RGB")
                    image.save(page_path, format="PNG", dpi=(args.dpi, args.dpi))
                    width, height = image.size
                derived_hash = sha256_file(page_path)
                duplicate = seen_hashes.get(derived_hash)
                if duplicate is None:
                    seen_hashes[derived_hash] = page_id
                page_records.append(
                    {
                        "page_id": page_id,
                        "logical_order": page_number,
                        "source_path": str(source),
                        "source_input_order": source_order,
                        "source_page_index": source_page_index,
                        "source_file_sha256": source_hash,
                        "derived_page_path": str(page_path.resolve()),
                        "derived_page_sha256": derived_hash,
                        "width_px": width,
                        "height_px": height,
                        "page_width_px": width,
                        "page_height_px": height,
                        "work_dpi": args.dpi,
                        "coordinate_system": "pixel",
                        "origin": "top-left",
                        "duplicate_candidate_of": duplicate,
                        "page_checks": {
                            "order": "pending-visual-review",
                            "missing_page": "pending-visual-review",
                            "rotation": "pending-visual-review",
                            "skew": "pending-visual-review",
                            "legibility": "pending-visual-review",
                            "edge_clipping": "pending-visual-review",
                        },
                    }
                )
            if temporary is not None:
                temporary.cleanup()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    visual_inventory_path = audit_dir / "visual-inventory.json"
    write_json(visual_inventory_path, {
        "kind": "visual-inventory",
        "version": 1,
        "status": "COMPLETE",
        "asset_count": 0,
        "reviewed_source_pages": [
            {"page_id": page["page_id"], "derived_page_sha256": page["derived_page_sha256"]}
            for page in page_records
        ],
    })
    fresh_passes = {
        name: {"completed": False, "source_reopened": False}
        for name in ("completeness", "formula", "text")
    }
    fresh_passes["visual-assets"] = {
        "completed": False,
        "source_reopened": False,
        "inventory_outcome": "no-visual-assets",
        "review_scope": "Pending reopened-source visual-object inventory.",
        "reviewed_asset_ids": [],
        "evidence": ["audit/visual-inventory.json"],
    }
    manifest = {
        "schema_version": "1.1",
        "status": "DRAFT-UNVERIFIED",
        "created_at": now_iso(),
        "preflight_path": str(args.preflight.resolve()),
        "source_files": source_files,
        "work_dpi": args.dpi,
        "coordinate_system": {"unit": "pixel", "origin": "top-left", "x1_y1": "exclusive"},
        "pages": page_records,
        "page_order_review": {
            "status": "pending-visual-review",
            "suspected_missing": [],
            "duplicate_candidates": [
                {"page_id": page["page_id"], "duplicate_candidate_of": page["duplicate_candidate_of"]}
                for page in page_records
                if page["duplicate_candidate_of"]
            ],
        },
        "questions": [],
        "figures": [],
        "tables": [],
        "uncertainties": [],
        "revision_history": [],
        "required_text_anchors": [],
        "fresh_passes": fresh_passes,
        "final_consistency": {},
    }
    write_json(job_dir / "manifest.json", manifest)
    print(str(job_dir / "manifest.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
