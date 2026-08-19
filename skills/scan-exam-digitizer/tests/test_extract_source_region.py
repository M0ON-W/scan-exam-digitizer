from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from helpers import make_image, run_script


class ExtractSourceRegionTests(unittest.TestCase):
    def test_crop_uses_top_left_pixel_bbox_and_records_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_image(root / "page.png", size=(100, 120))
            result = run_script(
                "extract_source_region.py",
                "--page",
                source,
                "--bbox",
                10,
                20,
                60,
                80,
                "--region-id",
                "p001-q01-fig01",
                "--output-dir",
                root / "regions",
                "--contrast",
                1.1,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with Image.open(root / "regions" / "p001-q01-fig01-raw.png") as raw:
                self.assertEqual(raw.size, (50, 60))
            log = json.loads((root / "regions" / "p001-q01-fig01.json").read_text(encoding="utf-8"))
            self.assertEqual(log["coordinate_system"], "pixel")
            self.assertEqual(log["origin"], "top-left")
            self.assertEqual(log["source_bbox"], {"x0": 10, "y0": 20, "x1": 60, "y1": 80})
            self.assertEqual(log["page_width_px"], 100)
            self.assertEqual(log["page_height_px"], 120)
            self.assertEqual(len(log["raw_sha256"]), 64)
            self.assertEqual(len(log["processed_sha256"]), 64)

    def test_invalid_bbox_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_image(root / "page.png", size=(100, 120))
            result = run_script(
                "extract_source_region.py",
                "--page",
                source,
                "--bbox",
                90,
                20,
                101,
                80,
                "--region-id",
                "bad",
                "--output-dir",
                root / "regions",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid bbox", (result.stdout + result.stderr).lower())
            self.assertFalse((root / "regions" / "bad.json").exists())


if __name__ == "__main__":
    unittest.main()
