from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from _common import compile_latex, executable_version, is_safe_identifier, render_pdf, resolve_executable, sha256_file, write_json


TAIL_LIMIT = 4000
VECTOR_BUILD_RECORD_KIND = "scan-exam-digitizer-vector-build"
VECTOR_BUILD_RECORD_SCHEMA_VERSION = "1.0"


def asset_id(value: str) -> str:
    if not is_safe_identifier(value):
        raise argparse.ArgumentTypeError(
            "unsafe asset ID; use letters, digits, dots, underscores, or hyphens without path separators"
        )
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile and rasterize a standalone vector LaTeX asset.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--latex-engine", required=True)
    parser.add_argument("--renderer", required=True)
    parser.add_argument("--asset-id", required=True, type=asset_id)
    return parser.parse_args()


def tail(value: str) -> str:
    return value[-TAIL_LIMIT:]


def resolved_name(value: str, executable: Path | None) -> str:
    return str(executable) if executable else value


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source = args.source.resolve()
    build_path = output_dir / f"{args.asset_id}-build.json"
    engine = resolve_executable(args.latex_engine)
    renderer = resolve_executable(args.renderer)
    source_sha256 = sha256_file(source) if source.is_file() else None
    stdout = ""
    stderr = ""
    pdf_path: Path | None = None
    rendered_pages: list[str] = []
    status = "FAIL"

    try:
        if not source.is_file():
            stderr = f"LaTeX source not found: {source}"
        else:
            with tempfile.TemporaryDirectory(prefix=f"{args.asset_id}-", dir=output_dir) as temporary:
                staging_dir = Path(temporary)
                compile_result = compile_latex(source, staging_dir, args.latex_engine)
                stdout += compile_result.get("stdout") or ""
                stderr += compile_result.get("stderr") or ""
                compiled_pdf = Path(compile_result["pdf_path"]) if compile_result.get("pdf_path") else None
                if compile_result["status"] == "PASS" and compiled_pdf and compiled_pdf.is_file():
                    pdf_path = output_dir / f"{args.asset_id}.pdf"
                    shutil.copyfile(compiled_pdf, pdf_path)
                    render_result = render_pdf(compiled_pdf, staging_dir / "render", args.renderer)
                    stdout += render_result.get("stdout") or ""
                    stderr += render_result.get("stderr") or ""
                    if render_result["status"] == "PASS":
                        for page_number, page in enumerate(render_result["pages"], start=1):
                            destination = output_dir / f"{args.asset_id}-page-{page_number:04d}.png"
                            shutil.copyfile(page, destination)
                            rendered_pages.append(str(destination.resolve()))
                        status = "PASS"
    except Exception as exc:
        stderr += ("\n" if stderr else "") + str(exc)

    record: dict[str, Any] = {
        "kind": VECTOR_BUILD_RECORD_KIND,
        "schema_version": VECTOR_BUILD_RECORD_SCHEMA_VERSION,
        "asset_id": args.asset_id,
        "source_path": str(source),
        "source_sha256": source_sha256,
        "engine": resolved_name(args.latex_engine, engine),
        "engine_version": executable_version(engine) if engine else None,
        "renderer": resolved_name(args.renderer, renderer),
        "renderer_version": executable_version(renderer) if renderer else None,
        "pdf_path": str(pdf_path.resolve()) if pdf_path and pdf_path.is_file() else None,
        "pdf_sha256": sha256_file(pdf_path) if pdf_path and pdf_path.is_file() else None,
        "rendered_pages": rendered_pages,
        "status": status,
        "stdout_tail": tail(stdout),
        "stderr_tail": tail(stderr),
    }
    write_json(build_path, record)
    if status != "PASS":
        print(record["stderr_tail"] or "Vector asset build failed.", file=sys.stderr)
        return 2
    print(record["pdf_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
