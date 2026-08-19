from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"


def run_script(name: str, *args: object, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPTS / name), *(str(arg) for arg in args)]
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(command, text=True, capture_output=True, env=merged_env, check=False)


def portable_tectonic() -> Path:
    configured = os.environ.get("SCAN_EXAM_TECTONIC")
    if configured:
        return Path(configured)
    if os.name != "nt":
        xelatex = shutil.which("xelatex")
        if xelatex:
            return Path(xelatex)
    candidates = (
        SKILL_ROOT.parent / "tools" / "tectonic" / "tectonic.exe",
        Path(r"D:\Gemini\模拟电子电路总复习\.agents\skills\tools\tectonic\tectonic.exe"),
        Path("/mnt/d/Gemini/模拟电子电路总复习/.agents/skills/tools/tectonic/tectonic.exe"),
    )
    return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])


def renderer() -> str:
    value = shutil.which("pdftoppm")
    if not value:
        raise RuntimeError("pdftoppm is required for tests")
    return value


def make_image(path: Path, size: tuple[int, int] = (240, 320), label: str = "PAGE") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 15, size[0] - 13, size[1] - 16), outline="black", width=3)
    draw.text((25, 30), label, fill="black")
    draw.line((25, 80, size[0] - 25, 80), fill="black", width=2)
    image.save(path)
    return path


def make_pdf(path: Path, text: str = "Searchable exam text") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=(360, 480))
    pdf.drawString(40, 430, text)
    pdf.drawString(40, 405, "Question 1")
    pdf.save()
    return path


def write_json(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def valid_manifest(status: str = "VERIFIED") -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "status": status,
        "source_files": [{"path": "source.png", "sha256": "a" * 64}],
        "work_dpi": 300,
        "pages": [],
        "questions": [],
        "uncertainties": [],
        "revision_history": [],
        "required_text_anchors": ["Searchable exam text", "Question 1"],
        "fresh_passes": {
            name: {"completed": True, "source_reopened": True}
            for name in ("completeness", "formula", "image", "text")
        },
        "final_consistency": {str(index): "answered" for index in range(1, 11)},
    }


def make_delivery_package(root: Path, manifest: dict[str, object] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    selected_manifest = manifest or valid_manifest()
    make_pdf(root / "exam-digital.pdf")
    (root / "exam.tex").write_text("Searchable exam text\\nQuestion 1", encoding="utf-8")
    (root / "figures").mkdir(exist_ok=True)
    write_json(root / "manifest.json", selected_manifest)
    (root / "check-report.md").write_text(
        "# 检查报告\n\n"
        "## 文档信息\n- Status: " + str(selected_manifest["status"]) + "\n\n"
        "## 完整性\n- 缺页：无\n\n"
        "## 公式检查\n- 待确认：0\n\n"
        "## 图片检查\n- 待确认：0\n\n"
        "## Fresh-pass 证据\n- 四轮均重新打开原扫描件\n\n"
        "## 人工确认项目\n无\n\n"
        "## 最终一致性\n1. answered\n2. answered\n3. answered\n4. answered\n"
        "5. answered\n6. answered\n7. answered\n8. answered\n9. answered\n10. answered\n\n"
        "## 声明\nVERIFIED 表示规定的源文件对照检查均已执行并通过，不构成绝对零错误保证。\n",
        encoding="utf-8",
    )
    return root
