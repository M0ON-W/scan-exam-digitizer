from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from reportlab.pdfgen import canvas

from helpers import run_script


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_package(root: Path, collision: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "figures").mkdir()
    (root / "audit").mkdir()

    pdf = root / "exam-digital.pdf"
    document = canvas.Canvas(str(pdf), pagesize=(468, 660))
    document.drawString(50, 620, "Semantic layout smoke")
    document.save()
    (root / "exam.tex").write_text("Semantic layout smoke", encoding="utf-8")

    raw_crop = root / "figures" / "A-Q1-01-raw.png"
    Image.new("RGB", (80, 60), "white").save(raw_crop)
    rendered = root / "figures" / "A-Q1-01.png"
    Image.new("RGB", (160, 100), "white").save(rendered)
    reconstruction = root / "figures" / "A-Q1-01.tex"
    reconstruction.write_text("% deterministic circuit source\n", encoding="utf-8")
    comparison = root / "figures" / "A-Q1-01-comparison.png"
    Image.new("RGB", (160, 100), "white").save(comparison)
    build_record = root / "figures" / "A-Q1-01-build.json"
    write_json(
        build_record,
        {
            "kind": "scan-exam-digitizer-vector-build",
            "schema_version": "1.0",
            "status": "PASS",
            "asset_id": "A-Q1-01",
            "source_sha256": sha256(reconstruction),
            "pdf_sha256": sha256(rendered),
            "engine": "Tectonic",
            "engine_version": "0.15.0",
            "renderer": "Pillow",
            "renderer_version": "10",
            "rendered_pages": ["figures/A-Q1-01.png"],
            "stdout_tail": "",
            "stderr_tail": "",
        },
    )

    label_bbox = {"x0": 100, "y0": 180, "x1": 120, "y1": 194}
    wire_bbox = {"x0": 150, "y0": 200, "x1": 360, "y1": 202}
    if collision:
        wire_bbox = {"x0": 105, "y0": 190, "x1": 360, "y1": 202}

    manifest = {
        "schema_version": "1.2",
        "status": "VERIFIED",
        "created_at": "2026-08-19T12:00:00+08:00",
        "source_files": [{"path": "source.png", "sha256": "a" * 64}],
        "work_dpi": 300,
        "pages": [
            {
                "page_id": "p001",
                "logical_order": 1,
                "source_path": "source.png",
                "source_file_sha256": "a" * 64,
                "derived_page_path": "pages/p001.png",
                "derived_page_sha256": "b" * 64,
                "page_width_px": 1200,
                "page_height_px": 1600,
            }
        ],
        "questions": [
            {
                "question_id": "Q1",
                "displayed_number": "1",
                "page_ids": ["p001"],
                "content_block_ids": [],
                "figure_ids": ["A-Q1-01"],
                "table_ids": [],
            }
        ],
        "figures": [
            {
                "asset_id": "A-Q1-01",
                "question_id": "Q1",
                "asset_type": "circuit",
                "reproduction_mode": "vector-redraw",
                "source_page_id": "p001",
                "source_bbox": {"x0": 100, "y0": 200, "x1": 600, "y1": 500},
                "raw_crop": "figures/A-Q1-01-raw.png",
                "raw_crop_sha256": sha256(raw_crop),
                "element_checklist": {
                    "components": 1,
                    "connections": 1,
                    "directions_checked": True,
                    "labels_checked": True,
                    "values_units_checked": True,
                    "orientation_checked": True,
                },
                "comparison_evidence": "figures/A-Q1-01-comparison.png",
                "qa_status": "PASS",
                "decision_reason": "Every visible circuit element was confirmed against the reopened source crop.",
                "reconstruction_source": "figures/A-Q1-01.tex",
                "rendered_asset": "figures/A-Q1-01.png",
                "rendered_asset_sha256": sha256(rendered),
                "build_record": "figures/A-Q1-01-build.json",
                "toolchain": {"engine": "Tectonic", "renderer": "Pillow"},
                "semantic_context": {
                    "question_function": "Determine the circuit's synchronous counter behavior.",
                    "asset_function": "Show the counter wiring and labeled control signals.",
                    "meaning_map": [
                        {
                            "source_element": "CLK",
                            "rendered_element": "CLK",
                            "meaning": "clock input controlling the counter state transition",
                        }
                    ],
                    "answer_inference_excluded": True,
                    "source_reopened": True,
                },
                "layout": {
                    "page_width_pt": 468,
                    "page_height_pt": 660,
                    "slot": {"x0": 40, "y0": 100, "x1": 420, "y1": 300},
                    "figure_width_fraction": 0.81,
                    "font_size_pt": 9,
                    "elements": [
                        {"id": "CLK", "kind": "label", "bbox": label_bbox},
                        {"id": "wire-1", "kind": "wire", "bbox": wire_bbox},
                    ],
                },
            }
        ],
        "tables": [],
        "uncertainties": [],
        "revision_history": [],
        "fresh_passes": {
            name: {"completed": True, "source_reopened": True}
            for name in ("completeness", "formula", "text")
        },
        "required_text_anchors": ["Semantic layout smoke"],
        "final_consistency": {str(index): "answered" for index in range(1, 11)},
    }
    manifest["fresh_passes"]["visual-assets"] = {
        "completed": True,
        "source_reopened": True,
        "review_scope": "All circuit assets in the package",
        "inventory_outcome": "assets-reviewed",
        "reviewed_asset_ids": ["A-Q1-01"],
        "evidence": ["audit/visual-qa.md"],
    }
    (root / "audit" / "visual-qa.md").write_text("Source and output compared by circuit elements.\n", encoding="utf-8")
    write_json(root / "manifest.json", manifest)
    (root / "check-report.md").write_text(
        "# 检查报告\n\n"
        "## 文档信息\n- 状态：VERIFIED\n\n"
        "## 完整性\n\n## 公式检查\n\n## 视觉对象检查\n\n"
        "## Fresh-pass 证据\n\n## 人工确认项目\n无\n\n"
        "## 最终一致性\n" + "\n".join(f"{i}. answered" for i in range(1, 11)) + "\n\n"
        "## 声明\nVERIFIED\n",
        encoding="utf-8",
    )
    return root


class SemanticLayoutContractTests(unittest.TestCase):
    def test_complete_semantic_and_layout_contract_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = make_package(Path(temporary) / "package")
            result = run_script("validate_deliverables.py", "--package-dir", package)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_layout_lint_rejects_a_label_wire_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = make_package(Path(temporary) / "package", collision=True)
            result = run_script("layout_lint.py", "--package-dir", package)
            output = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn("label", output.lower())
            self.assertIn("wire", output.lower())


if __name__ == "__main__":
    unittest.main()
