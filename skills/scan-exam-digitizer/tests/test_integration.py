from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from pypdf import PdfReader

from helpers import portable_tectonic, renderer, run_script
from integration_fixture import draft_phase, source_phase, verify_fixture_phase


class FullIntegrationTests(unittest.TestCase):
    def test_scan_to_searchable_latex_pdf_with_original_crop_and_qa_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_phase(root, portable_tectonic(), renderer())
            preflight = run_script(
                "preflight.py",
                "--input", root / "synthetic-scan.pdf",
                "--job-dir", root / "package",
                "--latex-engine", portable_tectonic(),
                "--renderer", renderer(),
                "--visual-read-confirmed",
                "--math-glyphs-confirmed",
            )
            self.assertEqual(preflight.returncode, 0, preflight.stdout + preflight.stderr)
            draft_phase(root, portable_tectonic(), renderer())
            result = verify_fixture_phase(root, "automated-integration-test")
            self.assertEqual(result["status"], "PASS")
            package = root / "package"
            self.assertTrue((package / "figures" / "Q2-figure-raw.png").exists())
            self.assertTrue((package / "comparisons" / "page-0001-side-by-side.png").exists())
            reader = PdfReader(str(package / "exam-digital.pdf"))
            self.assertEqual(len(reader.pages), 2)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            self.assertIn("大学期末考试", text)
            self.assertIn("English searchable anchor", text)
            manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue((package / manifest["source_files"][0]["path"]).exists())
            self.assertFalse(Path(manifest["source_files"][0]["path"]).is_absolute())
            for page in manifest["pages"]:
                self.assertFalse(Path(page["derived_page_path"]).is_absolute())
                self.assertTrue((package / page["derived_page_path"]).exists())


if __name__ == "__main__":
    unittest.main()
