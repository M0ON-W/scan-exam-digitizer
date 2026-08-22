#!/usr/bin/env python3
"""Crop a reviewed source region from a rendered scan page."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser(description="Crop a source image using pixel coordinates.")
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--bbox", nargs=4, type=int, required=True, metavar=("X0", "Y0", "X1", "Y1"))
    args = parser.parse_args()

    try:
        with Image.open(args.image) as source:
            x0, y0, x1, y1 = args.bbox
            if not (0 <= x0 < x1 <= source.width and 0 <= y0 < y1 <= source.height):
                raise ValueError(
                    f"Bounding box must stay within image size {source.width}x{source.height}"
                )
            crop = source.crop((x0, y0, x1, y1))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            crop.save(args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

