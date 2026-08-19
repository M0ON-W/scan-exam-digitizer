from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from helpers import run_script, write_json


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from _common import now_iso, read_json, render_pdf, resolve_executable, sha256_file  # noqa: E402


SOURCE_TEX = r"""\documentclass[12pt,a4paper]{article}
\usepackage[margin=22mm]{geometry}
\usepackage{fontspec,amsmath,graphicx,array}
\setmainfont{Times New Roman}
\IfFontExistsTF{Noto Serif CJK SC}{\newfontfamily\zhfont{Noto Serif CJK SC}}{\newfontfamily\zhfont{Microsoft YaHei}}
\begin{document}
\begin{center}{\zhfont\Large 大学期末考试（合成样例）}\\
{\zhfont 课程：信号与系统\quad 考试时间：120分钟}
\end{center}
{\zhfont 一、选择题（每题5分，共10分）}

1. {\zhfont 已知信号} \(x(t)=e^{-2t}u(t)\){\zhfont ，其拉普拉斯变换为（\quad）。}

A. \(\frac{1}{s-2}\)\quad B. \(\frac{1}{s+2}\)\quad C. \(s+2\)\quad D. \(s-2\)

2. {\zhfont 根据下图波形，写出对应题号，不得移动图题关系。}

\begin{center}\includegraphics[width=.62\linewidth]{source-figure.png}\end{center}

\newpage
{\zhfont 二、填空题（每题10分，共20分）}

3. {\zhfont 计算积分} \(\displaystyle \int_{-\infty}^{\infty} e^{-\alpha t^2}\,\mathrm{d}t=\underline{\hspace{5em}}\){\zhfont 。}

4. {\zhfont 填写下表：}

\begin{center}
\begin{tabular}{|c|c|}\hline
{\zhfont 符号} & {\zhfont 数值} \\\hline
\(\omega_0\) & \(2\pi\,\mathrm{rad/s}\) \\\hline
\(X(j\omega)\) & \(\begin{bmatrix}1&2\\3&4\end{bmatrix}\) \\\hline
\end{tabular}
\end{center}

English searchable anchor.
\end{document}
"""


DIGITAL_TEX = r"""\documentclass[12pt,a4paper]{article}
\usepackage[margin=22mm]{geometry}
\usepackage{fontspec,amsmath,graphicx,array}
\setmainfont{Times New Roman}
\IfFontExistsTF{Noto Serif CJK SC}{\newfontfamily\zhfont{Noto Serif CJK SC}}{\newfontfamily\zhfont{Microsoft YaHei}}
\begin{document}
\begin{center}{\zhfont\Large 大学期末考试（合成样例）}\\
{\zhfont 课程：信号与系统\quad 考试时间：120分钟}
\end{center}
{\zhfont 一、选择题（每题5分，共10分）}

1. {\zhfont 已知信号} \(x(t)=e^{-2t}u(t)\){\zhfont ，其拉普拉斯变换为（\quad）。}

A. \(\frac{1}{s-2}\)\quad B. \(\frac{1}{s+2}\)\quad C. \(s+2\)\quad D. \(s-2\)

2. {\zhfont 根据下图波形，写出对应题号，不得移动图题关系。}

\begin{center}\includegraphics[width=.62\linewidth]{figures/Q2-figure-processed.png}\end{center}

\newpage
{\zhfont 二、填空题（每题10分，共20分）}

3. {\zhfont 计算积分} \(\displaystyle \int_{-\infty}^{\infty} e^{-\alpha t^2}\,\mathrm{d}t=\underline{\hspace{5em}}\){\zhfont 。}

4. {\zhfont 填写下表：}

\begin{center}
\begin{tabular}{|c|c|}\hline
{\zhfont 符号} & {\zhfont 数值} \\\hline
\(\omega_0\) & \(2\pi\,\mathrm{rad/s}\) \\\hline
\(X(j\omega)\) & \(\begin{bmatrix}1&2\\3&4\end{bmatrix}\) \\\hline
\end{tabular}
\end{center}

English searchable anchor.
\end{document}
"""


def require(result: object, label: str) -> None:
    if getattr(result, "returncode") != 0:
        raise RuntimeError(f"{label} failed:\n{getattr(result, 'stdout')}\n{getattr(result, 'stderr')}")


def create_source_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (900, 360), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((5, 5, 894, 354), outline=(255, 0, 255), width=10)
    draw.line((80, 180, 820, 180), fill="black", width=5)
    draw.line((450, 45, 450, 315), fill="black", width=5)
    points = [(90, 180), (180, 75), (270, 180), (360, 285), (450, 180), (540, 75), (630, 180), (720, 285), (810, 180)]
    draw.line(points, fill="black", width=8)
    draw.polygon([(820, 180), (792, 165), (792, 195)], fill="black")
    draw.text((825, 190), "t", fill="black")
    image.save(path)


def source_phase(root: Path, engine: Path, renderer: str) -> dict[str, object]:
    source_dir = root / "synthetic-source"
    source_dir.mkdir(parents=True, exist_ok=True)
    create_source_figure(source_dir / "source-figure.png")
    source_tex = source_dir / "source-print.tex"
    source_tex.write_text(SOURCE_TEX, encoding="utf-8")
    build_dir = source_dir / "build"
    require(run_script("compile_exam.py", "--source", source_tex, "--output-dir", build_dir, "--engine", engine), "source compile")
    source_pdf = build_dir / "source-print.pdf"
    native_renderer = resolve_executable(renderer)
    if native_renderer is None:
        raise RuntimeError(f"Renderer unavailable: {renderer}")
    rendered = render_pdf(source_pdf, source_dir / "rendered" / "source-page", native_renderer, dpi=180)
    if rendered["status"] != "PASS" or len(rendered["pages"]) != 2:
        raise RuntimeError(f"Source render failed or did not produce two pages: {rendered}")
    images = []
    for page in rendered["pages"]:
        with Image.open(page) as opened:
            images.append(opened.convert("RGB"))
    scan_pdf = root / "synthetic-scan.pdf"
    images[0].save(scan_pdf, "PDF", save_all=True, append_images=images[1:], resolution=180.0, quality=95)
    for image in images:
        image.close()
    info = {
        "status": "PASS",
        "source_print_pdf": str(source_pdf.resolve()),
        "scan_pdf": str(scan_pdf.resolve()),
        "scan_pdf_sha256": sha256_file(scan_pdf),
        "rendered_pages": rendered["pages"],
    }
    write_json(root / "source-info.json", info)
    return info


def find_magenta_bbox(page: Path) -> tuple[int, int, int, int]:
    with Image.open(page) as opened:
        image = opened.convert("RGB")
    mask = Image.new("L", image.size, 0)
    pixels = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    mask.putdata([255 if r > 180 and b > 180 and g < 150 else 0 for r, g, b in pixels])
    bbox = mask.getbbox()
    image.close()
    mask.close()
    if bbox is None:
        raise RuntimeError("Unable to locate the original magenta-bordered figure in the scan.")
    x0, y0, x1, y1 = bbox
    return max(0, x0 - 8), max(0, y0 - 8), x1 + 8, y1 + 8


def report_text(status: str, source_name: str, fresh: bool) -> str:
    evidence = "四轮均重新打开原扫描件；记录见 manifest。" if fresh else "待执行。"
    return f"""# 检查报告

## 文档信息
- 原始文件：{source_name}
- 原始页数：2
- 输出页数：2
- 识别大题数：2
- 识别小题数：4
- 状态：{status}

## 完整性
- 缺页：无
- 漏题：无
- 漏图：无
- 页序异常：无
- 题号清单：第1题 ✓；第2题 ✓；第3题 ✓；第4题 ✓

## 公式检查
- 公式总数：10
- 已核对：10
- 待确认：0

## 视觉对象检查
- 视觉对象总数：2
- 已核对：2
- 待确认：0

## Fresh-pass 证据
- {evidence}

## 人工确认项目
无

## 最终一致性
1. 原扫描件 2 页。
2. 输出文档 2 页。
3. 共 2 道大题。
4. 共 4 道小题。
5. 不存在待确认内容。
6. 不存在未处理图片。
7. 不存在无法可靠识别的公式。
8. 不存在疑似缺页。
9. 题号 1–4 连续并与原卷一致。
10. 原题图片已对应第 2 题。

## 声明
VERIFIED 表示规定的源文件对照检查均已执行并通过，不构成绝对零错误保证。
"""


def draft_phase(root: Path, engine: Path, renderer: str) -> dict[str, object]:
    package = root / "package"
    preflight = package / "audit" / "preflight.json"
    if read_json(preflight).get("status") != "PASS":
        raise RuntimeError("Draft phase requires a passing PRE-FLIGHT in package/audit/preflight.json.")
    original_scan = root / "synthetic-scan.pdf"
    source_dir = package / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    scan_pdf = source_dir / "original-scan.pdf"
    shutil.copy2(original_scan, scan_pdf)
    require(
        run_script(
            "inspect_exam.py", "--input", scan_pdf, "--job-dir", package,
            "--preflight", preflight, "--dpi", 180, "--renderer", renderer,
        ),
        "page inspection",
    )
    manifest_path = package / "manifest.json"
    manifest = read_json(manifest_path)
    first_page = Path(manifest["pages"][0]["derived_page_path"])
    bbox = find_magenta_bbox(first_page)
    require(
        run_script(
            "extract_source_region.py", "--page", first_page, "--bbox", *bbox,
            "--region-id", "Q2-figure", "--output-dir", package / "figures", "--work-dpi", 180,
            "--source-file-sha256", manifest["pages"][0]["source_file_sha256"], "--contrast", 1.05,
        ),
        "figure crop",
    )
    figure_provenance_path = package / "figures" / "Q2-figure.json"
    figure_provenance = read_json(figure_provenance_path)
    figure_provenance["source_page"] = "pages/page-0001.png"
    figure_provenance["raw_path"] = "figures/Q2-figure-raw.png"
    figure_provenance["processed_path"] = "figures/Q2-figure-processed.png"
    write_json(figure_provenance_path, figure_provenance)
    page_by_id = {page["page_id"]: page for page in manifest["pages"]}
    page_two = page_by_id["p002"]
    table_raw = package / "figures" / "Q4-table-raw.png"
    shutil.copy2(package / page_two["derived_page_path"], table_raw)
    figure_asset = {
        "asset_id": "Q2-figure",
        "question_id": "Q2",
        "asset_type": "plot-waveform",
        "reproduction_mode": "source-crop",
        "source_page_id": "p001",
        "source_bbox": dict(zip(("x0", "y0", "x1", "y1"), bbox)),
        "raw_crop": "figures/Q2-figure-raw.png",
        "raw_crop_sha256": sha256_file(package / "figures" / "Q2-figure-raw.png"),
        "element_checklist": {
            "curves": 1,
            "axes_checked": True,
            "scale_ticks_checked": True,
            "arrows_checked": True,
            "labels_checked": True,
            "values_units_checked": True,
            "orientation_checked": True,
        },
        "comparison_evidence": "comparisons/comparison-index.json",
        "qa_status": "PASS",
        "decision_reason": "The waveform is retained as a provenance-preserving crop so its raster trace is not silently redrawn.",
        "fallback_reason": {
            "code": "irreproducible-source-detail",
            "affected_elements": ["curve"],
            "observations": [{
                "issue_code": "raster-pattern",
                "element_type": "curve",
                "element_id": "waveform-1",
                "page_id": "p001",
                "bbox": dict(zip(("x0", "y0", "x1", "y1"), bbox)),
                "evidence_ref": "figures/Q2-figure-raw.png",
            }],
        },
        "semantic_context": {
            "question_function": "Use the displayed waveform to identify or reason about the signal in question 2.",
            "asset_function": "Preserve the waveform's axes, arrow, trace, endpoint, and time label next to its owning prompt.",
            "meaning_map": [
                {"source_element": "waveform-1", "rendered_element": "waveform-1", "meaning": "signal trace and time orientation"},
                {"source_element": "t", "rendered_element": "t", "meaning": "time-axis label"},
            ],
            "answer_inference_excluded": True,
            "source_reopened": True,
        },
        "layout": {
            "page_width_pt": 595,
            "page_height_pt": 842,
            "slot": {"x0": 80, "y0": 470, "x1": 480, "y1": 650},
            "figure_width_fraction": 0.672,
            "font_size_pt": 9,
            "elements": [
                {"id": "axis-x", "kind": "axis", "bbox": {"x0": 100, "y0": 520, "x1": 460, "y1": 522}},
                {"id": "waveform-1", "kind": "curve", "bbox": {"x0": 130, "y0": 540, "x1": 420, "y1": 590}},
                {"id": "time-label", "kind": "label", "bbox": {"x0": 430, "y0": 600, "x1": 440, "y1": 612}},
            ],
        },
    }
    table_asset = {
        "asset_id": "T1",
        "table_id": "T1",
        "question_id": "Q4",
        "asset_type": "table",
        "reproduction_mode": "source-crop",
        "source_page_id": "p002",
        "source_bbox": {"x0": 0, "y0": 0, "x1": page_two["page_width_px"], "y1": page_two["page_height_px"]},
        "raw_crop": "figures/Q4-table-raw.png",
        "raw_crop_sha256": sha256_file(table_raw),
        "element_checklist": {
            "rows": 3,
            "columns": 2,
            "headers_checked": True,
            "merged_cells_checked": True,
            "formulas_units_checked": True,
            "cells_checked": True,
        },
        "comparison_evidence": "comparisons/comparison-index.json",
        "qa_status": "PASS",
        "decision_reason": "The table crop preserves the source cell relationships while the editable table is still under visual review.",
        "fallback_reason": {
            "code": "irreproducible-source-detail",
            "affected_elements": ["cell-content"],
            "observations": [{
                "issue_code": "raster-pattern",
                "element_type": "cell-content",
                "element_id": "table-cells",
                "page_id": "p002",
                "bbox": {"x0": 0, "y0": 0, "x1": page_two["page_width_px"], "y1": page_two["page_height_px"]},
                "evidence_ref": "figures/Q4-table-raw.png",
            }],
        },
        "semantic_context": {
            "question_function": "Complete or read the symbol/value table in question 4.",
            "asset_function": "Keep each symbol paired with its numeric value, unit, and formula relationship.",
            "meaning_map": [
                {"source_element": "symbol-column", "rendered_element": "symbol-column", "meaning": "symbol identifiers"},
                {"source_element": "value-column", "rendered_element": "value-column", "meaning": "numeric values and units"},
            ],
            "answer_inference_excluded": True,
            "source_reopened": True,
        },
        "layout": {
            "page_width_pt": 595,
            "page_height_pt": 842,
            "slot": {"x0": 70, "y0": 390, "x1": 525, "y1": 600},
            "table_width_fraction": 0.765,
            "font_size_pt": 9,
            "cell_padding_pt": 3.5,
            "row_heights_pt": [18, 18, 18],
        },
    }
    exam_tex = package / "exam.tex"
    exam_tex.write_text(DIGITAL_TEX, encoding="utf-8")
    build = package / "build"
    require(run_script("compile_exam.py", "--source", exam_tex, "--output-dir", build, "--engine", engine), "digital compile")
    shutil.copy2(build / "exam.pdf", package / "exam-digital.pdf")

    manifest.update(
        {
            "status": "DRAFT-UNVERIFIED",
            "questions": [
                {
                    "question_id": f"Q{number}",
                    "displayed_number": str(number),
                    "parent": "major-1" if number < 3 else "major-2",
                    "page_ids": ["p001" if number < 3 else "p002"],
                    "figure_ids": ["Q2-figure"] if number == 2 else [],
                    "table_ids": ["T1"] if number == 4 else [],
                    "content_block_ids": [],
                }
                for number in range(1, 5)
            ],
            "figures": [figure_asset],
            "tables": [table_asset],
            "required_text_anchors": ["大学期末考试", "English searchable anchor"],
            "final_consistency": {
                "1": "2", "2": "2", "3": "2", "4": "4", "5": "no", "6": "no",
                "7": "no", "8": "no", "9": "faithful and continuous", "10": "Q2 figure linked correctly",
            },
        }
    )
    manifest["preflight_path"] = "audit/preflight.json"
    for source in manifest["source_files"]:
        source["path"] = "source/original-scan.pdf"
    for page in manifest["pages"]:
        page["source_path"] = "source/original-scan.pdf"
        page["derived_page_path"] = f"pages/{Path(page['derived_page_path']).name}"
        page["page_checks"] = {
            "order": "fixture-known-correct",
            "missing_page": "none",
            "rotation": "correct",
            "skew": "none",
            "legibility": "clear",
            "edge_clipping": "none",
        }
    write_json(manifest_path, manifest)
    (package / "check-report.md").write_text(
        report_text("DRAFT-UNVERIFIED", "source/original-scan.pdf", fresh=False), encoding="utf-8"
    )
    require(
        run_script(
            "make_comparisons.py", "--manifest", manifest_path, "--output-pdf", package / "exam-digital.pdf",
            "--output-dir", package / "comparisons", "--renderer", renderer, "--dpi", 150,
        ),
        "comparison generation",
    )
    require(run_script("validate_deliverables.py", "--package-dir", package), "draft structural validation")
    result = {"status": "DRAFT-UNVERIFIED", "package": str(package.resolve()), "manifest": str(manifest_path.resolve())}
    write_json(root / "draft-result.json", result)
    return result


def verify_fixture_phase(root: Path, reviewer: str) -> dict[str, object]:
    package = root / "package"
    manifest_path = package / "manifest.json"
    manifest = read_json(manifest_path)
    relative_pages = [Path(page["derived_page_path"]) for page in manifest["pages"]]
    pages = [package / page for page in relative_pages]
    fresh: dict[str, object] = {}
    scopes = {
        "completeness": "2 pages; 2 major questions; questions 1-4; options, scores, formula, figure, and table presence; no merge/split",
        "formula": "e^{-2t}; s±2 fractions; infinite integral; alpha t^2; omega_0; X(jomega); rad/s; 2x2 matrix",
        "text": "title, course, 120-minute time, wording, numbering, scores, case, punctuation, numeric values, and units",
    }
    for name in ("completeness", "formula", "text"):
        hashes = []
        for page in pages:
            with Image.open(page) as opened:
                opened.load()
            hashes.append(sha256_file(page))
        fresh[name] = {
            "completed": True,
            "source_reopened": True,
            "completed_at": now_iso(),
            "reviewer": reviewer,
            "review_scope": scopes[name],
            "evidence": [page.as_posix() for page in relative_pages],
            "source_hashes": hashes,
            "findings": ["No discrepancy found in the synthetic fixture fresh pass."],
        }
    fresh["visual-assets"] = {
        "completed": True,
        "source_reopened": True,
        "completed_at": now_iso(),
        "reviewer": reviewer,
        "review_scope": "Q2 waveform crop and Q4 symbol/value table",
        "inventory_outcome": "assets-reviewed",
        "reviewed_asset_ids": ["Q2-figure", "T1"],
        "evidence": ["comparisons/comparison-index.json", "audit/layout-lint.json"],
        "findings": ["Every visual asset was compared against its reopened source region and layout contract."],
    }
    manifest["fresh_passes"] = fresh
    manifest["status"] = "VERIFIED"
    write_json(manifest_path, manifest)
    (package / "check-report.md").write_text(
        report_text("VERIFIED", "source/original-scan.pdf", fresh=True), encoding="utf-8"
    )
    require(run_script("validate_deliverables.py", "--package-dir", package), "verified delivery validation")
    validation = read_json(package / "audit" / "validation.json")
    result = {
        "status": validation["status"],
        "manifest_status": manifest["status"],
        "package": str(package.resolve()),
        "validation": str((package / "audit" / "validation.json").resolve()),
    }
    write_json(root / "integration-result.json", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the synthetic end-to-end fixture without installing the skill.")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--engine", required=True, type=Path)
    parser.add_argument("--renderer", required=True)
    parser.add_argument("--phase", choices=("source", "draft", "verify-fixture"), required=True)
    parser.add_argument("--reviewer", default="automated-integration-fixture")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.phase == "source":
        result = source_phase(root, args.engine.resolve(), args.renderer)
    elif args.phase == "draft":
        result = draft_phase(root, args.engine.resolve(), args.renderer)
    else:
        result = verify_fixture_phase(root, args.reviewer)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
