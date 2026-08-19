from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import make_image, portable_tectonic, renderer, run_script

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import preflight


class PreflightTests(unittest.TestCase):
    def test_fontconfig_alias_resolves_to_concrete_fontspec_family(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["fc-match"], returncode=0, stdout="Liberation Serif", stderr=""
        )
        with patch.object(preflight, "resolve_executable", return_value=Path("/usr/bin/fc-match")), patch.object(
            preflight.subprocess, "run", return_value=completed
        ):
            resolved, evidence = preflight.resolve_font_family("Times New Roman")

        self.assertEqual(resolved, "Liberation Serif")
        self.assertEqual(evidence["requested"], "Times New Roman")
        self.assertEqual(evidence["resolved"], "Liberation Serif")

    def test_font_resolution_falls_back_when_fontconfig_is_unavailable(self) -> None:
        with patch.object(preflight, "resolve_executable", return_value=None):
            resolved, evidence = preflight.resolve_font_family("Times New Roman")

        self.assertEqual(resolved, "Times New Roman")
        self.assertEqual(evidence["resolver"], "fallback")

    def test_preflight_proves_chinese_math_compile_render_and_extract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_image(root / "source.png")
            result = run_script(
                "preflight.py",
                "--input",
                source,
                "--job-dir",
                root / "job",
                "--latex-engine",
                portable_tectonic(),
                "--renderer",
                renderer(),
                "--visual-read-confirmed",
                "--math-glyphs-confirmed",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads((root / "job" / "audit" / "preflight.json").read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "PASS")
            for capability in (
                "visual_page_read",
                "image_crop",
                "file_generation",
                "latex_compile",
                "pdf_render",
                "pdf_text_extract",
                "math_glyphs_visual",
            ):
                self.assertEqual(data["capabilities"][capability]["status"], "PASS")
            self.assertIn("中文正文", data["extracted_text"])
            self.assertIn("English searchable text", data["extracted_text"])
            self.assertEqual(
                set(data["latex_smoke_features"]),
                {"fraction", "superscript", "subscript", "infinite_integral", "greek", "matrix"},
            )

    def test_preflight_blocks_when_latex_engine_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_image(root / "source.png")
            result = run_script(
                "preflight.py",
                "--input",
                source,
                "--job-dir",
                root / "job",
                "--latex-engine",
                root / "missing-engine.exe",
                "--renderer",
                renderer(),
                "--visual-read-confirmed",
                "--math-glyphs-confirmed",
            )
            self.assertNotEqual(result.returncode, 0)
            data = json.loads((root / "job" / "audit" / "preflight.json").read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "BLOCKED")
            self.assertEqual(data["capabilities"]["latex_compile"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
