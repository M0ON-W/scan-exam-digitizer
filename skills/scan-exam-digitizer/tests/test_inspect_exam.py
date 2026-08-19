from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from helpers import make_image, run_script, write_json


class InspectExamTests(unittest.TestCase):
    def test_manifest_records_pixel_geometry_hashes_and_duplicate_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = make_image(root / "first.png", size=(200, 300), label="SAME")
            second = root / "second.png"
            second.write_bytes(first.read_bytes())
            preflight = write_json(root / "preflight.json", {"status": "PASS"})

            result = run_script(
                "inspect_exam.py",
                "--input",
                first,
                "--input",
                second,
                "--job-dir",
                root / "job",
                "--preflight",
                preflight,
                "--dpi",
                300,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads((root / "job" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["work_dpi"], 300)
            self.assertEqual(len(manifest["pages"]), 2)
            first_page = manifest["pages"][0]
            self.assertEqual((first_page["width_px"], first_page["height_px"]), (200, 300))
            self.assertEqual(len(first_page["source_file_sha256"]), 64)
            self.assertEqual(len(first_page["derived_page_sha256"]), 64)
            self.assertEqual(manifest["pages"][1]["duplicate_candidate_of"], first_page["page_id"])
            self.assertEqual(manifest["uncertainties"], [])
            self.assertEqual(manifest["revision_history"], [])

    def test_inspection_refuses_unpassed_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_image(root / "source.png")
            preflight = write_json(root / "preflight.json", {"status": "BLOCKED"})
            result = run_script(
                "inspect_exam.py",
                "--input",
                source,
                "--job-dir",
                root / "job",
                "--preflight",
                preflight,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("pre-flight status is not pass", (result.stdout + result.stderr).lower())
            self.assertFalse((root / "job" / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
