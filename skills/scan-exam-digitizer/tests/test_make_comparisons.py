from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from helpers import make_image, make_pdf, renderer, run_script, write_json


class MakeComparisonsTests(unittest.TestCase):
    def test_creates_full_page_comparison_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_page = make_image(root / "page-0001.png", size=(360, 480))
            manifest = write_json(
                root / "manifest.json",
                {
                    "pages": [
                        {
                            "page_id": "p001",
                            "derived_page_path": str(source_page),
                            "width_px": 360,
                            "height_px": 480,
                        }
                    ]
                },
            )
            output_pdf = make_pdf(root / "exam.pdf")
            result = run_script(
                "make_comparisons.py",
                "--manifest",
                manifest,
                "--output-pdf",
                output_pdf,
                "--output-dir",
                root / "comparisons",
                "--renderer",
                renderer(),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            index = json.loads((root / "comparisons" / "comparison-index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["page_count"], 1)
            self.assertTrue((root / "comparisons" / "page-0001-side-by-side.png").exists())


if __name__ == "__main__":
    unittest.main()
