from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import compile_latex, extract_pdf_text, now_iso, sha256_file, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile an exam LaTeX source and record reproducible evidence.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--engine", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source = args.source.resolve()
    result = compile_latex(source, output_dir, args.engine)
    log = (result.get("stdout") or "") + ("\n" if result.get("stdout") else "") + (result.get("stderr") or "")
    (output_dir / "compile.log").write_text(log, encoding="utf-8")

    pdf_path = Path(result["pdf_path"]) if result.get("pdf_path") else None
    extracted = ""
    extraction_error = None
    if result["status"] == "PASS" and pdf_path:
        try:
            extracted = extract_pdf_text(pdf_path)
        except Exception as exc:  # reported as a separate check; compilation evidence remains intact
            extraction_error = str(exc)

    metadata = {
        "status": result["status"],
        "created_at": now_iso(),
        "source": str(source),
        "source_sha256": sha256_file(source) if source.exists() else None,
        "engine": result.get("engine"),
        "command": result.get("command"),
        "returncode": result.get("returncode"),
        "pdf_path": str(pdf_path) if pdf_path else None,
        "pdf_sha256": sha256_file(pdf_path) if pdf_path and pdf_path.exists() else None,
        "text_extraction_status": "PASS" if extracted.strip() else "FAIL",
        "text_extraction_error": extraction_error,
        "log_path": str((output_dir / "compile.log").resolve()),
    }
    write_json(output_dir / "compile-result.json", metadata)
    if result["status"] != "PASS":
        print(result.get("stderr") or "LaTeX compilation failed.", file=sys.stderr)
        return 2
    print(str(pdf_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
