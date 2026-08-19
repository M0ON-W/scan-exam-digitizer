from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def is_safe_identifier(value: object) -> bool:
    """Return whether value is a portable single-component artifact identifier."""
    return isinstance(value, str) and bool(SAFE_IDENTIFIER.fullmatch(value))


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def resolve_executable(value: str | Path) -> Path | None:
    candidate = Path(value)
    if candidate.exists() and candidate.is_file():
        candidate = candidate.resolve()
        if candidate.suffix.lower() in {".cmd", ".bat"}:
            executable_name = candidate.stem + ".exe"
            for ancestor in candidate.parents:
                for relative in (
                    Path("Library") / "bin" / executable_name,
                    Path("native") / "poppler" / "Library" / "bin" / executable_name,
                ):
                    native = ancestor / relative
                    if native.exists() and native.is_file():
                        return native.resolve()
        return candidate
    located = shutil.which(str(value))
    return resolve_executable(Path(located)) if located else None


def executable_version(value: str | Path) -> str | None:
    executable = resolve_executable(value)
    if executable is None:
        return None
    for flag in ("--version", "-version", "-v"):
        try:
            result = run_process([str(executable), flag], timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            continue
        output = (result.stdout or result.stderr).strip()
        if result.returncode == 0 and output:
            return output.splitlines()[0]
    return None


def run_process(
    command: list[str],
    cwd: Path | None = None,
    timeout: int = 180,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    effective_command = command
    if Path(command[0]).suffix.lower() in {".cmd", ".bat"}:
        command_line = " ".join(f'"{item}"' for item in command)
        effective_command = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", command_line]
    return subprocess.run(
        effective_command,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=timeout,
        env=env,
    )


def compile_latex(source: Path, output_dir: Path, engine_value: str | Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    requested_name = Path(engine_value).stem.lower()
    engine = resolve_executable(engine_value)
    if engine is None:
        return {
            "status": "FAIL",
            "engine": str(engine_value),
            "command": [],
            "returncode": None,
            "stdout": "",
            "stderr": f"LaTeX engine not found: {engine_value}",
            "pdf_path": None,
        }

    supported_names = {"tectonic", "xelatex", "lualatex"}
    name = requested_name if requested_name in supported_names else engine.stem.lower()
    if name == "tectonic":
        command = [str(engine), "--keep-logs", "--print", "--outdir", str(output_dir.resolve()), source.name]
    elif name in {"xelatex", "lualatex"}:
        command = [
            str(engine),
            *([f"-fmt={name}"] if engine.stem.lower() != name else []),
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            f"-output-directory={output_dir.resolve()}",
            source.name,
        ]
    else:
        return {
            "status": "FAIL",
            "engine": str(engine),
            "command": [],
            "returncode": None,
            "stdout": "",
            "stderr": "Unsupported LaTeX engine; use XeLaTeX, LuaLaTeX, or Tectonic.",
            "pdf_path": None,
        }

    try:
        process_env = os.environ.copy()
        if name == "tectonic":
            cache = Path(
                process_env.get("SCAN_EXAM_TECTONIC_CACHE", "")
                or (Path(tempfile.gettempdir()) / "scan-exam-digitizer-tectonic-cache")
            ).resolve()
            cache.mkdir(parents=True, exist_ok=True)
            process_env["TECTONIC_CACHE_DIR"] = str(cache)
        result = run_process(command, cwd=source.parent, timeout=300, env=process_env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "FAIL",
            "engine": str(engine),
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "pdf_path": None,
        }

    pdf = output_dir / f"{source.stem}.pdf"
    status = "PASS" if result.returncode == 0 and pdf.exists() and pdf.stat().st_size > 0 else "FAIL"
    return {
        "status": status,
        "engine": str(engine),
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "pdf_path": str(pdf.resolve()) if pdf.exists() else None,
    }


def natural_page_key(path: Path) -> tuple[int, str]:
    tail = path.stem.rsplit("-", 1)[-1]
    return (int(tail) if tail.isdigit() else 10**9, path.name)


def render_pdf(pdf: Path, output_prefix: Path, renderer_value: str | Path, dpi: int = 150) -> dict[str, Any]:
    renderer = resolve_executable(renderer_value)
    if renderer is None:
        return {"status": "FAIL", "stderr": f"PDF renderer not found: {renderer_value}", "pages": []}
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    command = [str(renderer), "-png", "-r", str(dpi), str(pdf.resolve()), str(output_prefix.resolve())]
    try:
        result = run_process(command, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "FAIL", "command": command, "stderr": str(exc), "pages": []}
    pages = sorted(output_prefix.parent.glob(f"{output_prefix.name}-*.png"), key=natural_page_key)
    status = "PASS" if result.returncode == 0 and pages else "FAIL"
    return {
        "status": status,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "pages": [str(path.resolve()) for path in pages],
    }


def extract_pdf_text(pdf: Path) -> str:
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf)).pages)
