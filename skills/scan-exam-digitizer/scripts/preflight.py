from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

from _common import compile_latex, extract_pdf_text, now_iso, render_pdf, resolve_executable, sha256_file, write_json
from check_dependencies import evaluate_capabilities, load_dependency_map


SMOKE_TEX = r"""\documentclass{article}
\usepackage{fontspec}
\usepackage{amsmath}
\setmainfont{__LATIN_FONT__}
\newfontfamily\zhfont{__CJK_FONT__}
\begin{document}
{\zhfont 中文正文可搜索。} English searchable text.
\[
\frac{x_1^2}{y_2}+\int_{-\infty}^{\infty}e^{-\alpha t}\,\mathrm{d}t
+\omega_0+\begin{bmatrix}1&2\\3&4\end{bmatrix}
\]
\end{document}
"""

FEATURES = ["fraction", "superscript", "subscript", "infinite_integral", "greek", "matrix"]
ASSET_CAPABILITY_GROUPS = {
    "table": "table",
    "block-diagram": "block-diagram",
    "signal-flow": "signal-flow",
    "circuit": "circuit",
    "plot-waveform": "plot-waveform",
}
DEFAULT_DEPENDENCY_MAP = Path(__file__).resolve().parents[1] / "assets" / "dependencies.json"
PREFLIGHT_REPORT_KIND = "scan-exam-digitizer-preflight"
PREFLIGHT_REPORT_SCHEMA_VERSION = "1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the blocking scan-exam digitization PRE-FLIGHT.")
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--job-dir", required=True, type=Path)
    parser.add_argument("--latex-engine", required=True)
    parser.add_argument("--renderer", required=True)
    parser.add_argument("--visual-read-confirmed", action="store_true")
    parser.add_argument("--math-glyphs-confirmed", action="store_true")
    parser.add_argument("--asset-type", action="append", choices=sorted(ASSET_CAPABILITY_GROUPS))
    parser.add_argument("--dependency-map", type=Path, default=DEFAULT_DEPENDENCY_MAP)
    return parser.parse_args()


def capability(status: str, evidence: object, note: str = "") -> dict[str, object]:
    return {"status": status, "evidence": evidence, "note": note}


def resolve_font_family(requested: str) -> tuple[str, dict[str, object]]:
    """Resolve a Fontconfig alias to the concrete family fontspec can load."""
    matcher = resolve_executable("fc-match")
    if matcher is None:
        return requested, {
            "requested": requested,
            "resolved": requested,
            "resolver": "fallback",
            "note": "fc-match is unavailable; using the requested family name.",
        }
    try:
        result = subprocess.run(
            [str(matcher), "-f", "%{family[0]}", requested],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return requested, {
            "requested": requested,
            "resolved": requested,
            "resolver": str(matcher),
            "note": f"Font resolution failed; using the requested family name: {exc}",
        }
    resolved = result.stdout.strip()
    if result.returncode != 0 or not resolved or any(character in resolved for character in "{}\\\r\n"):
        return requested, {
            "requested": requested,
            "resolved": requested,
            "resolver": str(matcher),
            "note": "Font resolution returned no safe family name; using the requested family name.",
            "stderr": result.stderr.strip(),
        }
    return resolved, {
        "requested": requested,
        "resolved": resolved,
        "resolver": str(matcher),
        "note": "Resolved to the concrete Fontconfig family name used by fontspec.",
    }


def resolve_cjk_font_family() -> tuple[str | None, dict[str, object]]:
    finder = resolve_executable("fc-list")
    if finder is None:
        return None, {
            "status": "FAIL",
            "resolver": "fallback",
            "note": "No CJK-capable font can be verified because fc-list is unavailable.",
        }
    try:
        result = subprocess.run([str(finder), "-f", "%{family[0]}\\n", ":lang=zh"], text=True, capture_output=True, check=False)
    except OSError as exc:
        return None, {"status": "FAIL", "resolver": str(finder), "note": str(exc)}
    family = next((line.split(",", 1)[0].strip() for line in result.stdout.splitlines() if line.strip()), "")
    if result.returncode != 0 or not family or any(character in family for character in "{}\\\r\n"):
        return None, {
            "status": "FAIL",
            "resolver": str(finder),
            "note": "No CJK-capable font is installed for the Chinese LaTeX smoke test.",
            "stderr": result.stderr.strip(),
        }
    return family, {
        "status": "PASS",
        "resolver": str(finder),
        "resolved": family,
        "note": "Resolved a Fontconfig family with Chinese glyph coverage.",
    }


def inputs_openable(paths: list[Path]) -> tuple[bool, str]:
    try:
        for path in paths:
            if not path.exists() or not path.is_file():
                return False, f"Missing input: {path}"
            if path.suffix.lower() == ".pdf":
                from pypdf import PdfReader

                if len(PdfReader(str(path)).pages) < 1:
                    return False, f"PDF has no pages: {path}"
            else:
                with Image.open(path) as image:
                    image.verify()
        return True, "All inputs can be opened."
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    args = parse_args()
    job_dir = args.job_dir.resolve()
    audit_dir = job_dir / "audit"
    smoke_dir = audit_dir / "preflight-smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    report_path = audit_dir / "preflight.json"
    inputs = [path.resolve() for path in args.input]
    capabilities: dict[str, dict[str, object]] = {}

    openable, open_note = inputs_openable(inputs)
    capabilities["visual_page_read"] = capability(
        "PASS" if openable and args.visual_read_confirmed else "FAIL",
        [str(path) for path in inputs],
        open_note if args.visual_read_confirmed else open_note + " Visual-read capability not attested.",
    )

    try:
        probe = Image.new("L", (24, 24), "white")
        crop = probe.crop((2, 3, 18, 20))
        crop_path = smoke_dir / "crop-probe.png"
        crop.save(crop_path)
        crop_ok = crop.size == (16, 17) and crop_path.exists()
        capabilities["image_crop"] = capability("PASS" if crop_ok else "FAIL", str(crop_path))
    except Exception as exc:
        capabilities["image_crop"] = capability("FAIL", None, str(exc))

    try:
        write_probe = smoke_dir / "write-probe.txt"
        write_probe.write_text("scan-exam-digitizer preflight", encoding="utf-8")
        capabilities["file_generation"] = capability("PASS", str(write_probe))
    except Exception as exc:
        capabilities["file_generation"] = capability("FAIL", None, str(exc))

    latin_font, latin_font_resolution = resolve_font_family("Times New Roman")
    cjk_font, cjk_font_resolution = resolve_cjk_font_family()
    smoke_tex = SMOKE_TEX.replace("__LATIN_FONT__", latin_font).replace("__CJK_FONT__", cjk_font or "DejaVu Sans")
    smoke_source = smoke_dir / "latex-smoke.tex"
    smoke_source.write_text(smoke_tex, encoding="utf-8")
    engine = resolve_executable(args.latex_engine)
    if cjk_font is None:
        compile_result = {
            "status": "FAIL",
            "engine": str(args.latex_engine),
            "stderr": cjk_font_resolution["note"],
            "pdf_path": None,
        }
    elif engine is None:
        compile_result = {
            "status": "FAIL",
            "engine": str(args.latex_engine),
            "stderr": f"LaTeX engine not found: {args.latex_engine}",
            "pdf_path": None,
        }
    else:
        compile_result = compile_latex(smoke_source, smoke_dir, args.latex_engine)
    capabilities["latex_compile"] = capability(
        compile_result["status"],
        compile_result.get("pdf_path"),
        compile_result.get("stderr", "")[-2000:],
    )
    (smoke_dir / "latex-smoke-compile.log").write_text(
        (compile_result.get("stdout") or "") + "\n" + (compile_result.get("stderr") or ""), encoding="utf-8"
    )

    rendered_pages: list[str] = []
    pdf_path = Path(compile_result["pdf_path"]) if compile_result.get("pdf_path") else None
    if pdf_path and pdf_path.exists():
        render_result = render_pdf(pdf_path, smoke_dir / "latex-smoke-page", args.renderer, dpi=180)
        rendered_pages = render_result.get("pages", [])
        capabilities["pdf_render"] = capability(
            render_result["status"], rendered_pages, render_result.get("stderr", "")[-2000:]
        )
    else:
        capabilities["pdf_render"] = capability("FAIL", [], "No compiled PDF to render.")

    extracted = ""
    extraction_note = ""
    if pdf_path and pdf_path.exists():
        try:
            extracted = extract_pdf_text(pdf_path)
            anchors_ok = "中文正文" in extracted and "English searchable text" in extracted
            capabilities["pdf_text_extract"] = capability(
                "PASS" if anchors_ok else "FAIL", ["中文正文", "English searchable text"],
                "Both anchors extracted." if anchors_ok else "One or more body-text anchors were not extracted."
            )
        except Exception as exc:
            extraction_note = str(exc)
            capabilities["pdf_text_extract"] = capability("FAIL", None, extraction_note)
    else:
        capabilities["pdf_text_extract"] = capability("FAIL", None, "No compiled PDF to extract.")

    suspect_glyphs = [glyph for glyph in ("□", "�", "▯") if glyph in extracted]
    glyph_ok = bool(rendered_pages) and args.math_glyphs_confirmed and not suspect_glyphs
    capabilities["math_glyphs_visual"] = capability(
        "PASS" if glyph_ok else "FAIL",
        rendered_pages,
        "Visual glyph check attested and no suspect extraction characters found."
        if glyph_ok
        else "Rendered smoke page requires an actual visual missing-glyph check before attestation.",
    )

    requested_asset_types = list(dict.fromkeys(args.asset_type or []))
    requested_capabilities = {"base"}
    requested_capabilities.update(ASSET_CAPABILITY_GROUPS[asset_type] for asset_type in requested_asset_types)
    try:
        dependency_map = load_dependency_map(args.dependency_map)
        dependency_exit, dependency_report = evaluate_capabilities(
            dependency_map,
            requested_capabilities,
            dependency_map_sha256=sha256_file(args.dependency_map),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        dependency_exit = 2
        dependency_report = {
            "status": "BLOCKED",
            "fallback_capabilities": [],
            "error": str(exc),
        }
    fallback_asset_types = [
        asset_type
        for asset_type in requested_asset_types
        if ASSET_CAPABILITY_GROUPS[asset_type] in dependency_report.get("fallback_capabilities", [])
    ]
    available_reconstruction_modes = {
        asset_type: "source-crop" if asset_type in fallback_asset_types else "editable"
        for asset_type in requested_asset_types
    }
    base_capabilities_pass = all(item["status"] == "PASS" for item in capabilities.values())
    overall = "PASS" if base_capabilities_pass and dependency_exit != 2 else "BLOCKED"
    report = {
        "kind": PREFLIGHT_REPORT_KIND,
        "schema_version": PREFLIGHT_REPORT_SCHEMA_VERSION,
        "status": overall,
        "created_at": now_iso(),
        "inputs": [{"path": str(path), "sha256": sha256_file(path) if path.exists() else None} for path in inputs],
        "capabilities": capabilities,
        "requested_asset_types": requested_asset_types,
        "dependency_status": dependency_report["status"],
        "dependency_result": dependency_report,
        "available_reconstruction_modes": available_reconstruction_modes,
        "fallback_asset_types": fallback_asset_types,
        "latex_smoke_features": FEATURES,
        "font_resolution": {
            "latin": latin_font_resolution,
            "cjk": cjk_font_resolution,
        },
        "smoke_source": str(smoke_source),
        "smoke_pdf": str(pdf_path) if pdf_path else None,
        "smoke_rendered_pages": rendered_pages,
        "extracted_text": extracted,
        "suspect_glyphs": suspect_glyphs,
        "operator_attestations": {
            "visual_read_confirmed": args.visual_read_confirmed,
            "math_glyphs_confirmed": args.math_glyphs_confirmed,
        },
    }
    write_json(report_path, report)
    if overall != "PASS":
        failed = ", ".join(name for name, item in capabilities.items() if item["status"] != "PASS")
        print(f"PRE-FLIGHT BLOCKED: {failed}", file=sys.stderr)
        return 2
    print(str(report_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
