#!/usr/bin/env python3
"""Compile a LaTeX exam and render every PDF page for visual inspection."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

import pymupdf


def compile_source(source: Path, output_dir: Path, engine: str) -> Path:
    executable = shutil.which(engine)
    if not executable:
        raise RuntimeError(f"LaTeX engine not found: {engine}")
    output_dir.mkdir(parents=True, exist_ok=True)

    if Path(executable).stem.lower().startswith("tectonic"):
        command = [executable, source.name, "--outdir", str(output_dir)]
    else:
        command = [
            executable,
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={output_dir}",
            source.name,
        ]
    result = subprocess.run(
        command,
        cwd=source.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()
        raise RuntimeError(f"LaTeX compilation failed\n{detail[-6000:]}")

    pdf = output_dir / f"{source.stem}.pdf"
    if not pdf.exists():
        raise RuntimeError(f"Compilation succeeded but PDF was not found: {pdf}")
    return pdf


def render_pdf(pdf: Path, output_dir: Path, dpi: int) -> int:
    if dpi <= 0:
        raise ValueError("DPI must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(pdf)
    matrix = pymupdf.Matrix(dpi / 72, dpi / 72)
    for index, page in enumerate(document, start=1):
        page.get_pixmap(matrix=matrix, alpha=False).save(output_dir / f"page-{index:03d}.png")
    count = len(document)
    document.close()
    return count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile one year-specific LaTeX exam and render every output page."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--engine", default="xelatex", choices=("xelatex", "lualatex", "tectonic"))
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args()

    source = args.source.resolve()
    output_dir = args.output_dir.resolve()
    try:
        pdf = compile_source(source, output_dir, args.engine)
        page_count = render_pdf(pdf, output_dir / "rendered-pages", args.dpi)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Compiled {pdf} and rendered {page_count} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
