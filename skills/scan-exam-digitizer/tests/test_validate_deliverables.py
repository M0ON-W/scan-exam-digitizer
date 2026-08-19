from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from helpers import make_delivery_package, run_script, valid_manifest, write_json


class ValidateDeliverablesTests(unittest.TestCase):
    def validate(self, package: Path) -> tuple[int, dict[str, object], str]:
        result = run_script("validate_deliverables.py", "--package-dir", package)
        data = json.loads((package / "audit" / "validation.json").read_text(encoding="utf-8"))
        return result.returncode, data, result.stdout + result.stderr

    def test_verified_package_passes_with_complete_source_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = make_delivery_package(Path(temporary) / "package")
            code, data, output = self.validate(package)
            self.assertEqual(code, 0, output)
            self.assertEqual(data["status"], "PASS")

    def test_verified_rejects_active_uncertainty(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = valid_manifest()
            manifest["uncertainties"] = [
                {
                    "uncertainty_id": "U-001",
                    "status": "unresolved",
                    "current_value": "[待人工确认]",
                }
            ]
            package = make_delivery_package(Path(temporary) / "package", manifest)
            code, data, _ = self.validate(package)
            self.assertNotEqual(code, 0)
            self.assertIn("VERIFIED cannot contain unresolved uncertainties", data["errors"])

    def test_user_confirmation_history_is_traceable_and_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = valid_manifest()
            manifest["uncertainties"] = [
                {"uncertainty_id": "U-017", "status": "resolved", "current_value": "5"}
            ]
            manifest["revision_history"] = [
                {
                    "uncertainty_id": "U-017",
                    "previous_value": "[待人工确认]",
                    "current_value": "5",
                    "confirmed_by": "user",
                    "confirmed_at": "2026-08-11T16:00:00+08:00",
                    "note": "User confirmed U-017 as 5.",
                }
            ]
            package = make_delivery_package(Path(temporary) / "package", manifest)
            code, data, output = self.validate(package)
            self.assertEqual(code, 0, output)
            self.assertEqual(data["status"], "PASS")

    def test_invalid_confirmation_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = valid_manifest()
            manifest["revision_history"] = [
                {
                    "uncertainty_id": "U-017",
                    "previous_value": "[待人工确认]",
                    "current_value": "5",
                    "confirmed_by": "model",
                    "confirmed_at": "2026-08-11T16:00:00+08:00",
                    "note": "Model inferred it.",
                }
            ]
            package = make_delivery_package(Path(temporary) / "package", manifest)
            code, data, _ = self.validate(package)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("confirmed_by" in error for error in data["errors"]))

    def test_missing_fresh_pass_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = valid_manifest()
            manifest["fresh_passes"]["formula"]["source_reopened"] = False
            package = make_delivery_package(Path(temporary) / "package", manifest)
            code, data, _ = self.validate(package)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("fresh pass" in error for error in data["errors"]))

    def test_manifest_and_report_status_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = make_delivery_package(Path(temporary) / "package")
            report = package / "check-report.md"
            report.write_text(report.read_text(encoding="utf-8").replace("Status: VERIFIED", "Status: DRAFT-UNVERIFIED"), encoding="utf-8")
            code, data, _ = self.validate(package)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("report status" in error for error in data["errors"]))

    def test_blocked_preflight_rejects_noncanonical_stop_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = make_delivery_package(Path(temporary) / "package", valid_manifest("BLOCKED"))
            (package / "exam-digital.pdf").unlink()
            (package / "exam.tex").unlink()
            (package / "figures").rmdir()
            write_json(package / "audit" / "preflight.json", {"status": "BLOCKED", "capabilities": {}})
            code, data, output = self.validate(package)
            self.assertNotEqual(code, 0, output)
            self.assertTrue(any("canonical BLOCKED PRE-FLIGHT" in error for error in data["errors"]))
            self.assertFalse((package / "exam-digital.pdf").exists())


if __name__ == "__main__":
    unittest.main()
