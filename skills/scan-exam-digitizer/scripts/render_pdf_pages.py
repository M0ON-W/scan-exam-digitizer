#!/usr/bin/env python3
"""Render every page of a PDF to PNG for visual inspection."""

from __future__ import annotations

import argparse
from pathlib import Path

import pymupdf


def render(pdf_path: Path, output_dir: Path, dpi: int) -> list[Path]:
    if dpi <= 0:
        raise ValueError("DPI must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(pdf_path)
    scale = dpi / 72
    matrix = pymupdf.Matrix(scale, scale)
    outputs: list[Path] = []
    for index, page in enumerate(document, start=1):
        output = output_dir / f"page-{index:03d}.png"
        page.get_pixmap(matrix=matrix, alpha=False).save(output)
        outputs.append(output)
    document.close()
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Render all PDF pages to PNG images.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args()

    try:
        outputs = render(args.pdf, args.output_dir, args.dpi)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(f"Rendered {len(outputs)} pages to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
