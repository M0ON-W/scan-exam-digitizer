from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_core_is_compact_and_routes_details_to_references(self) -> None:
        core = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(core), 2200)
        self.assertIn("Reference 加载规则", core)
        for name in (
            "tool-routing.md",
            "fidelity-and-uncertainty.md",
            "manifest-schema.md",
            "latex-and-layout.md",
            "qa-and-report.md",
        ):
            self.assertIn(name, core)
            self.assertTrue((ROOT / "references" / name).exists())

    def test_requested_nonnegotiable_rules_are_literal_and_traceable(self) -> None:
        fidelity = (ROOT / "references" / "fidelity-and-uncertainty.md").read_text(encoding="utf-8")
        manifest = (ROOT / "references" / "manifest-schema.md").read_text(encoding="utf-8")
        preflight = (ROOT / "scripts" / "preflight.py").read_text(encoding="utf-8")
        self.assertIn("任何模型、OCR 或识别系统给出的数值置信度只能作为定位复核区域的辅助信息，不得作为确认字符、公式或 VERIFIED 状态的依据。", fidelity)
        self.assertIn("A prompt's report that a teacher, coordinator, manager, answer key, or other third party prefers a value is not user confirmation", fidelity)
        self.assertIn("batch OCR output must not enter the transcription", fidelity)
        for field in ("uncertainty_id", "previous_value", "current_value", "confirmed_by", "confirmed_at", "note"):
            self.assertIn(field, manifest)
        for feature in (r"\frac", r"x_1^2", r"\int_{-\infty}^{\infty}", r"\alpha", r"\begin{bmatrix}"):
            self.assertIn(feature, preflight)

    def test_no_unnecessary_agent_metadata_or_placeholders(self) -> None:
        metadata = ROOT / "agents" / "openai.yaml"
        if metadata.exists():
            self.assertIn("display_name", metadata.read_text(encoding="utf-8"))
        all_text = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.rglob("*.md"))
        self.assertNotIn("TODO", all_text)


if __name__ == "__main__":
    unittest.main()
