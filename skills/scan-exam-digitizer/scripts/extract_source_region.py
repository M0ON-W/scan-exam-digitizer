from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from _common import is_safe_identifier, now_iso, sha256_file, write_json


def region_id(value: str) -> str:
    if not is_safe_identifier(value):
        raise argparse.ArgumentTypeError(
            "unsafe region ID; use letters, digits, dots, underscores, or hyphens without path separators or leading dots"
        )
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crop an original scan region while preserving pixel provenance.")
    parser.add_argument("--page", required=True, type=Path)
    parser.add_argument("--bbox", nargs=4, required=True, type=int, metavar=("X0", "Y0", "X1", "Y1"))
    parser.add_argument("--region-id", required=True, type=region_id)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--work-dpi", type=int, default=300)
    parser.add_argument("--source-file-sha256")
    parser.add_argument("--rotate", type=float, default=0.0)
    parser.add_argument("--contrast", type=float, default=1.0)
    parser.add_argument("--autocontrast", action="store_true")
    parser.add_argument("--sharpen", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    page = args.page.resolve()
    output_dir = args.output_dir.resolve()
    x0, y0, x1, y1 = args.bbox
    if not page.exists():
        print(f"Page image not found: {page}", file=sys.stderr)
        return 2
    if args.work_dpi <= 0 or args.contrast <= 0:
        print("Work DPI and contrast must be positive.", file=sys.stderr)
        return 2
    try:
        with Image.open(page) as opened:
            source = opened.convert("RGB")
            width, height = source.size
            if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
                print(
                    f"Invalid bbox: expected 0 <= x0 < x1 <= {width} and 0 <= y0 < y1 <= {height}.",
                    file=sys.stderr,
                )
                return 2
            raw = source.crop((x0, y0, x1, y1))
    except Exception as exc:
        print(f"Unable to read or crop page image: {exc}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / f"{args.region_id}-raw.png"
    processed_path = output_dir / f"{args.region_id}-processed.png"
    raw.save(raw_path, format="PNG", dpi=(args.work_dpi, args.work_dpi))
    processed = raw.copy()
    operations: list[dict[str, object]] = []
    if args.rotate:
        processed = processed.rotate(args.rotate, resample=Image.Resampling.BICUBIC, expand=True, fillcolor="white")
        operations.append({"operation": "rotate", "degrees_counterclockwise": args.rotate})
    if args.autocontrast:
        processed = ImageOps.autocontrast(processed)
        operations.append({"operation": "autocontrast"})
    if args.contrast != 1.0:
        processed = ImageEnhance.Contrast(processed).enhance(args.contrast)
        operations.append({"operation": "contrast", "factor": args.contrast})
    if args.sharpen:
        processed = processed.filter(ImageFilter.UnsharpMask(radius=1.0, percent=110, threshold=3))
        operations.append({"operation": "unsharp_mask", "radius": 1.0, "percent": 110, "threshold": 3})
    processed.save(processed_path, format="PNG", dpi=(args.work_dpi, args.work_dpi))

    metadata = {
        "region_id": args.region_id,
        "created_at": now_iso(),
        "source_page": str(page),
        "source_page_sha256": sha256_file(page),
        "source_file_sha256": args.source_file_sha256,
        "coordinate_system": "pixel",
        "origin": "top-left",
        "x1_y1": "exclusive",
        "source_bbox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
        "page_width_px": width,
        "page_height_px": height,
        "work_dpi": args.work_dpi,
        "operations": operations,
        "raw_path": str(raw_path),
        "processed_path": str(processed_path),
        "raw_sha256": sha256_file(raw_path),
        "processed_sha256": sha256_file(processed_path),
    }
    write_json(output_dir / f"{args.region_id}.json", metadata)
    print(str(processed_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
