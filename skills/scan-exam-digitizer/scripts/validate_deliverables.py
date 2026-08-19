from __future__ import annotations

import argparse
import math
import re
import sys
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any

from _common import extract_pdf_text, now_iso, read_json, sha256_file, write_json


ALLOWED_STATUSES = {"BLOCKED", "DRAFT-UNVERIFIED", "VERIFIED"}
SUPPORTED_SCHEMA_VERSIONS = {"1.0", "1.1"}
CONFIRMATION_SOURCES = {"source-visual", "user"}
LEGACY_FRESH_PASSES = ("completeness", "formula", "image", "text")
SCHEMA_1_1_FRESH_PASSES = ("completeness", "formula", "visual-assets", "text")
REVISION_FIELDS = ("uncertainty_id", "previous_value", "current_value", "confirmed_by", "confirmed_at", "note")
LEGACY_REPORT_HEADINGS = (
    "文档信息",
    "完整性",
    "公式检查",
    "图片检查",
    "Fresh-pass 证据",
    "人工确认项目",
    "最终一致性",
    "声明",
)
SCHEMA_1_1_REPORT_HEADINGS = (
    "文档信息",
    "完整性",
    "公式检查",
    "视觉对象检查",
    "Fresh-pass 证据",
    "人工确认项目",
    "最终一致性",
    "声明",
)
CHECKLIST_CONTRACTS = {
    "table": {
        "counts": ("rows", "columns"),
        "booleans": ("headers_checked", "merged_cells_checked", "formulas_units_checked", "cells_checked"),
    },
    "block-diagram": {
        "counts": ("nodes", "connections"),
        "booleans": ("directions_checked", "labels_checked", "values_units_checked", "orientation_checked"),
    },
    "signal-flow": {
        "counts": ("nodes", "connections"),
        "booleans": ("directions_checked", "labels_checked", "values_units_checked", "orientation_checked"),
    },
    "circuit": {
        "counts": ("components", "connections"),
        "booleans": ("directions_checked", "labels_checked", "values_units_checked", "orientation_checked"),
    },
    "plot-waveform": {
        "counts": ("curves",),
        "booleans": ("axes_checked", "scale_ticks_checked", "arrows_checked", "labels_checked", "values_units_checked", "orientation_checked"),
    },
}
FALLBACK_REASON_CODES = {
    "source-uncertainty",
    "irreproducible-source-detail",
    "conditional-capability-unavailable",
}
FALLBACK_CAPABILITY_BY_ASSET_TYPE = {
    "table": "table",
    "block-diagram": "block-diagram",
    "signal-flow": "signal-flow",
    "circuit": "circuit",
    "plot-waveform": "plot-waveform",
}
FALLBACK_AFFECTED_ELEMENTS = {
    "table": {"cell-content", "merged-cell", "formula", "value", "unit", "border", "alignment"},
    "block-diagram": {"node", "connection", "direction", "branch", "summing-point", "sign", "label", "value", "unit", "grouping", "orientation"},
    "signal-flow": {"node", "connection", "direction", "branch", "summing-point", "sign", "label", "value", "unit", "grouping", "orientation"},
    "circuit": {"component", "connection", "terminal", "junction", "wire", "polarity", "direction", "value", "label", "unit", "reference-designator", "orientation"},
    "plot-waveform": {"axis", "scale-tick", "curve", "point", "arrow", "label", "value", "unit", "domain-range", "orientation", "shading", "hand-drawn-trace"},
}
OBSERVATION_ISSUE_CODES = {
    "source-uncertainty": {"ambiguous-mark", "blurred", "occluded", "unreadable"},
    "irreproducible-source-detail": {"freehand-trace", "non-deterministic-curve", "occluded", "raster-pattern", "shaded-trace"},
}
CANONICAL_PREFLIGHT_EVIDENCE = "audit/preflight.json"
PREFLIGHT_REPORT_KIND = "scan-exam-digitizer-preflight"
PREFLIGHT_REPORT_SCHEMA_VERSION = "1.0"
DEPENDENCY_MAP_PATH = Path(__file__).resolve().parents[1] / "assets" / "dependencies.json"
DEPENDENCY_MAP_KIND = "scan-exam-digitizer-dependency-map"
DEPENDENCY_REPORT_KIND = "scan-exam-digitizer-dependency-report"
DEPENDENCY_REPORT_SCHEMA_VERSION = "1.0"
VECTOR_BUILD_RECORD_KIND = "scan-exam-digitizer-vector-build"
VECTOR_BUILD_RECORD_SCHEMA_VERSION = "1.0"
PREFLIGHT_CAPABILITY_EVIDENCE_SHAPES = {
    "visual_page_read": "list",
    "image_crop": "path-or-null",
    "file_generation": "path-or-null",
    "latex_compile": "path-or-null",
    "pdf_render": "list",
    "pdf_text_extract": "list-or-null",
    "math_glyphs_visual": "list",
}
PREFLIGHT_SMOKE_FEATURES = ["fraction", "superscript", "subscript", "infinite_integral", "greek", "matrix"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a scan-exam-digitizer delivery package.")
    parser.add_argument("--package-dir", required=True, type=Path)
    return parser.parse_args()


def report_status(text: str) -> str | None:
    match = re.search(r"(?:Status|状态)\s*[:：]\s*(BLOCKED|DRAFT-UNVERIFIED|VERIFIED)", text, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def canonical_blocked_preflight(record: object, manifest: dict[str, Any]) -> bool:
    """Accept only a complete, reproducible BLOCKED PRE-FLIGHT record."""
    state = canonical_preflight_dependency_state(record)
    if not isinstance(record, dict) or not state or record.get("status") != "BLOCKED":
        return False
    if not valid_timestamp(record.get("created_at")) or record.get("latex_smoke_features") != PREFLIGHT_SMOKE_FEATURES:
        return False

    source_files = manifest.get("source_files")
    inputs = record.get("inputs")
    if not isinstance(source_files, list) or not source_files or not isinstance(inputs, list) or not inputs:
        return False
    source_hashes: list[str] = []
    for source in source_files:
        if not isinstance(source, dict) or not isinstance(source.get("path"), str) or not source["path"].strip():
            return False
        digest = source.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            return False
        source_hashes.append(digest.lower())
    input_hashes: list[str] = []
    for item in inputs:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            return False
        if not isinstance(item.get("path"), str) or not item["path"].strip():
            return False
        digest = item.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            return False
        input_hashes.append(digest.lower())
    if sorted(input_hashes) != sorted(source_hashes):
        return False

    capabilities = record.get("capabilities")
    if not isinstance(capabilities, dict) or set(capabilities) != set(PREFLIGHT_CAPABILITY_EVIDENCE_SHAPES):
        return False
    for name, shape in PREFLIGHT_CAPABILITY_EVIDENCE_SHAPES.items():
        item = capabilities.get(name)
        if not isinstance(item, dict) or set(item) != {"status", "evidence", "note"}:
            return False
        status = item.get("status")
        note = item.get("note")
        evidence = item.get("evidence")
        if status not in {"PASS", "FAIL"} or not isinstance(note, str):
            return False
        if shape == "list" and (not isinstance(evidence, list) or any(not isinstance(value, str) or not value for value in evidence)):
            return False
        if shape == "list-or-null" and evidence is not None and (
            not isinstance(evidence, list) or any(not isinstance(value, str) or not value for value in evidence)
        ):
            return False
        if shape == "path-or-null" and evidence is not None and (not isinstance(evidence, str) or not evidence.strip()):
            return False
        if status == "PASS" and evidence is None:
            return False
        if status == "FAIL":
            if not note.strip():
                return False

    font_resolution = record.get("font_resolution")
    attestations = record.get("operator_attestations")
    if (
        not isinstance(font_resolution, dict)
        or set(font_resolution) != {"latin", "cjk"}
        or any(not isinstance(value, dict) for value in font_resolution.values())
        or not isinstance(record.get("smoke_source"), str)
        or not record["smoke_source"].strip()
        or (record.get("smoke_pdf") is not None and not isinstance(record.get("smoke_pdf"), str))
        or not isinstance(record.get("smoke_rendered_pages"), list)
        or any(not isinstance(value, str) or not value for value in record["smoke_rendered_pages"])
        or not isinstance(record.get("extracted_text"), str)
        or not isinstance(record.get("suspect_glyphs"), list)
        or any(not isinstance(value, str) for value in record["suspect_glyphs"])
        or not isinstance(attestations, dict)
        or set(attestations) != {"visual_read_confirmed", "math_glyphs_confirmed"}
        or any(not isinstance(value, bool) for value in attestations.values())
    ):
        return False
    return state["dependency_status"] == "BLOCKED"


def valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_revision_history(manifest: dict[str, Any], errors: list[str]) -> None:
    revisions = manifest.get("revision_history", [])
    uncertainties = manifest.get("uncertainties", [])
    if not isinstance(revisions, list):
        errors.append("revision_history must be an array")
        return
    uncertainty_by_id = {
        item.get("uncertainty_id"): item
        for item in uncertainties
        if isinstance(item, dict) and item.get("uncertainty_id")
    } if isinstance(uncertainties, list) else {}
    matching_revisions: dict[str, list[dict[str, Any]]] = {}
    for index, revision in enumerate(revisions):
        label = f"revision_history[{index}]"
        if not isinstance(revision, dict):
            errors.append(f"{label} must be an object")
            continue
        missing = [field for field in REVISION_FIELDS if field not in revision]
        if missing:
            errors.append(f"{label} missing fields: {', '.join(missing)}")
            continue
        if revision.get("confirmed_by") not in CONFIRMATION_SOURCES:
            errors.append(f"{label}.confirmed_by must be source-visual or user")
        if not valid_timestamp(revision.get("confirmed_at")):
            errors.append(f"{label}.confirmed_at must be an ISO-8601 timestamp")
        if not isinstance(revision.get("note"), str) or not revision["note"].strip():
            errors.append(f"{label}.note must be non-empty")
        uncertainty_id = str(revision.get("uncertainty_id"))
        matching_revisions.setdefault(uncertainty_id, []).append(revision)

    for uncertainty_id, item in uncertainty_by_id.items():
        if item.get("status") == "resolved":
            history = matching_revisions.get(str(uncertainty_id), [])
            if not history:
                errors.append(f"resolved uncertainty {uncertainty_id} has no revision history")
            elif history[-1].get("current_value") != item.get("current_value"):
                errors.append(f"resolved uncertainty {uncertainty_id} does not match its latest revision current_value")


def read_editable_source(package: Path, errors: list[str]) -> str:
    source = package / "exam.tex"
    if not source.is_file():
        message = "editable source exam.tex cannot be read"
        if message not in errors:
            errors.append(message)
        return ""
    try:
        return source.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        message = "editable source exam.tex cannot be decoded as UTF-8"
    except OSError:
        message = "editable source exam.tex cannot be read"
    if message not in errors:
        errors.append(message)
    return ""


def is_non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_element_checklist(asset: dict[str, Any], label: str, errors: list[str]) -> None:
    asset_type = asset.get("asset_type")
    if asset_type not in CHECKLIST_CONTRACTS:
        allowed = ", ".join(CHECKLIST_CONTRACTS)
        errors.append(f"{label} asset_type must be one of: {allowed}")
        return
    checklist = asset.get("element_checklist")
    if not isinstance(checklist, dict) or not checklist:
        errors.append(f"{label} element_checklist is required and must be a non-empty object")
        return
    contract = CHECKLIST_CONTRACTS[asset_type]
    required_keys = (*contract["counts"], *contract["booleans"])
    missing = [key for key in required_keys if key not in checklist]
    if missing:
        errors.append(f"{label} element_checklist for {asset_type} is missing required keys: {', '.join(missing)}")
    for key in contract["counts"]:
        if key in checklist and not is_non_negative_integer(checklist[key]):
            errors.append(f"{label} element_checklist.{key} must be a finite non-negative integer")
    for key in contract["booleans"]:
        if key in checklist and not isinstance(checklist[key], bool):
            errors.append(f"{label} element_checklist.{key} must be a boolean")


def is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _legacy_canonical_preflight_proves_fallback(record: object, asset_type: object, capability_name: object) -> bool:
    """Accept only the complete, canonical PRE-FLIGHT proof for a source-crop fallback."""
    if not isinstance(asset_type, str) or not isinstance(capability_name, str) or not isinstance(record, dict):
        return False
    if record.get("kind") != PREFLIGHT_REPORT_KIND or record.get("schema_version") != PREFLIGHT_REPORT_SCHEMA_VERSION:
        return False
    if record.get("status") != "PASS" or record.get("dependency_status") != "DEGRADED":
        return False
    requested_types = record.get("requested_asset_types")
    fallback_types = record.get("fallback_asset_types")
    modes = record.get("available_reconstruction_modes")
    if (
        not isinstance(requested_types, list)
        or asset_type not in requested_types
        or not isinstance(fallback_types, list)
        or asset_type not in fallback_types
        or not isinstance(modes, dict)
        or modes.get(asset_type) != "source-crop"
    ):
        return False
    try:
        dependency_map = read_json(DEPENDENCY_MAP_PATH)
    except Exception:
        return False
    if (
        not isinstance(dependency_map, dict)
        or dependency_map.get("kind") != DEPENDENCY_MAP_KIND
        or dependency_map.get("schema_version") != DEPENDENCY_REPORT_SCHEMA_VERSION
        or not isinstance(dependency_map.get("capabilities"), dict)
        or not isinstance(dependency_map.get("requirements"), dict)
    ):
        return False
    map_capabilities = dependency_map["capabilities"]
    map_requirements = dependency_map["requirements"]
    map_capability = map_capabilities.get(capability_name)
    if not isinstance(map_capability, dict):
        return False
    dependency_result = record.get("dependency_result")
    if (
        not isinstance(dependency_result, dict)
        or dependency_result.get("kind") != DEPENDENCY_REPORT_KIND
        or dependency_result.get("schema_version") != DEPENDENCY_REPORT_SCHEMA_VERSION
        or dependency_result.get("dependency_map_sha256") != sha256_file(DEPENDENCY_MAP_PATH)
        or dependency_result.get("status") != "DEGRADED"
    ):
        return False
    requested_capabilities = dependency_result.get("requested_capabilities")
    fallback_capabilities = dependency_result.get("fallback_capabilities")
    capabilities = dependency_result.get("capabilities")
    requirements = dependency_result.get("requirements")
    if (
        not isinstance(requested_capabilities, list)
        or capability_name not in requested_capabilities
        or any(not isinstance(item, str) or item not in map_capabilities for item in requested_capabilities)
        or not isinstance(fallback_capabilities, list)
        or capability_name not in fallback_capabilities
        or not isinstance(capabilities, dict)
        or not isinstance(requirements, dict)
    ):
        return False
    capability_result = capabilities.get(capability_name)
    map_requirement_ids = map_capability.get("requirements")
    if (
        not isinstance(capability_result, dict)
        or capability_result.get("status") != "FAIL"
        or capability_result.get("degradable") is not map_capability.get("degradable")
        or not isinstance(map_requirement_ids, list)
    ):
        return False
    required_ids = capability_result.get("requirements")
    missing_ids = capability_result.get("missing_requirements")
    if (
        not isinstance(required_ids, list)
        or required_ids != map_requirement_ids
        or not isinstance(missing_ids, list)
        or not missing_ids
        or any(not isinstance(item, str) or item not in map_requirement_ids for item in missing_ids)
    ):
        return False
    failed_ids: list[str] = []
    for requirement_id in map_requirement_ids:
        map_requirement = map_requirements.get(requirement_id)
        probe = requirements.get(requirement_id)
        if not isinstance(map_requirement, dict):
            return False
        if (
            not isinstance(probe, dict)
            or probe.get("id") != requirement_id
            or probe.get("type") != map_requirement.get("type")
            or probe.get("installation_hint") != map_requirement.get("installation_hint")
        ):
            return False
        requirement_type = map_requirement.get("type")
        declaration_fields = {
            "python_module": ("import_name",),
            "tex_package": ("package",),
            "executable": ("candidates",),
            "cjk_font": ("candidates",),
        }.get(requirement_type)
        if declaration_fields is None or any(probe.get(field) != map_requirement.get(field) for field in declaration_fields):
            return False
        probe_status = probe.get("status")
        if probe_status == "FAIL":
            if probe.get("evidence") is not None or not isinstance(probe.get("note"), str) or not probe["note"].strip():
                return False
            failed_ids.append(requirement_id)
        elif probe_status == "PASS":
            if probe.get("evidence") is None or probe.get("note") != "":
                return False
        else:
            return False
    if missing_ids != failed_ids:
        return False
    for requirement_id, probe in requirements.items():
        if not isinstance(requirement_id, str) or requirement_id not in map_requirements or not isinstance(probe, dict):
            return False
        map_requirement = map_requirements[requirement_id]
        if (
            not isinstance(map_requirement, dict)
            or probe.get("id") != requirement_id
            or probe.get("type") != map_requirement.get("type")
            or probe.get("installation_hint") != map_requirement.get("installation_hint")
        ):
            return False
        declaration_fields = {
            "python_module": ("import_name",),
            "tex_package": ("package",),
            "executable": ("candidates",),
            "cjk_font": ("candidates",),
        }.get(map_requirement.get("type"))
        if declaration_fields is None or any(probe.get(field) != map_requirement.get(field) for field in declaration_fields):
            return False
        if probe.get("status") == "FAIL":
            if probe.get("evidence") is not None or not isinstance(probe.get("note"), str) or not probe["note"].strip():
                return False
        elif probe.get("status") == "PASS":
            if probe.get("evidence") is None or probe.get("note") != "":
                return False
        else:
            return False
    return True


def canonical_preflight_dependency_state(record: object) -> dict[str, object] | bool:
    """Validate the shared PRE-FLIGHT dependency closure and derive its canonical state."""
    if not isinstance(record, dict):
        return False
    if record.get("kind") != PREFLIGHT_REPORT_KIND or record.get("schema_version") != PREFLIGHT_REPORT_SCHEMA_VERSION:
        return False
    try:
        dependency_map = read_json(DEPENDENCY_MAP_PATH)
    except Exception:
        return False
    if (
        not isinstance(dependency_map, dict)
        or dependency_map.get("kind") != DEPENDENCY_MAP_KIND
        or dependency_map.get("schema_version") != DEPENDENCY_REPORT_SCHEMA_VERSION
        or not isinstance(dependency_map.get("capabilities"), dict)
        or not isinstance(dependency_map.get("requirements"), dict)
    ):
        return False
    map_capabilities = dependency_map["capabilities"]
    map_requirements = dependency_map["requirements"]
    if (
        not all(isinstance(name, str) and isinstance(capability, dict) for name, capability in map_capabilities.items())
        or not all(isinstance(name, str) and isinstance(requirement, dict) for name, requirement in map_requirements.items())
    ):
        return False

    requested_types = record.get("requested_asset_types")
    if (
        not isinstance(requested_types, list)
        or any(not isinstance(item, str) or item not in FALLBACK_CAPABILITY_BY_ASSET_TYPE for item in requested_types)
        or len(requested_types) != len(set(requested_types))
    ):
        return False
    direct_capabilities = {"base", *(FALLBACK_CAPABILITY_BY_ASSET_TYPE[item] for item in requested_types)}
    if not direct_capabilities.issubset(map_capabilities):
        return False

    dependency_result = record.get("dependency_result")
    if (
        not isinstance(dependency_result, dict)
        or dependency_result.get("kind") != DEPENDENCY_REPORT_KIND
        or dependency_result.get("schema_version") != DEPENDENCY_REPORT_SCHEMA_VERSION
        or dependency_result.get("dependency_map_sha256") != sha256_file(DEPENDENCY_MAP_PATH)
    ):
        return False
    requested_capabilities = dependency_result.get("requested_capabilities")
    capabilities = dependency_result.get("capabilities")
    requirements = dependency_result.get("requirements")
    if (
        not isinstance(requested_capabilities, list)
        or any(not isinstance(item, str) or item not in map_capabilities for item in requested_capabilities)
        or len(requested_capabilities) != len(set(requested_capabilities))
        or set(requested_capabilities) != direct_capabilities
        or not isinstance(capabilities, dict)
        or not isinstance(requirements, dict)
        or dependency_result.get("unknown_capabilities") != []
    ):
        return False

    selected: set[str] = set()
    pending = list(requested_capabilities)
    while pending:
        name = pending.pop()
        if name in selected:
            continue
        capability = map_capabilities.get(name)
        if not isinstance(capability, dict):
            return False
        parents = capability.get("requires", [])
        if not isinstance(parents, list) or any(not isinstance(parent, str) or parent not in map_capabilities for parent in parents):
            return False
        selected.add(name)
        pending.extend(parents)
    if set(capabilities) != selected:
        return False

    expected_requirements: set[str] = set()
    for name in selected:
        requirement_ids = map_capabilities[name].get("requirements")
        if not isinstance(requirement_ids, list) or any(not isinstance(requirement_id, str) for requirement_id in requirement_ids):
            return False
        expected_requirements.update(requirement_ids)
    if set(requirements) != expected_requirements:
        return False
    for requirement_id in expected_requirements:
        map_requirement = map_requirements.get(requirement_id)
        probe = requirements.get(requirement_id)
        if not isinstance(map_requirement, dict) or not isinstance(probe, dict):
            return False
        if (
            probe.get("id") != requirement_id
            or probe.get("type") != map_requirement.get("type")
            or probe.get("installation_hint") != map_requirement.get("installation_hint")
        ):
            return False
        declaration_fields = {
            "python_module": ("import_name",),
            "tex_package": ("package",),
            "executable": ("candidates",),
            "cjk_font": ("candidates",),
        }.get(map_requirement.get("type"))
        if declaration_fields is None or any(probe.get(field) != map_requirement.get(field) for field in declaration_fields):
            return False
        if probe.get("status") == "FAIL":
            if probe.get("evidence") is not None or not isinstance(probe.get("note"), str) or not probe["note"].strip():
                return False
        elif probe.get("status") == "PASS":
            if probe.get("evidence") is None or probe.get("note") != "":
                return False
        else:
            return False

    expected_fallbacks: list[str] = []
    blocking = False
    for name in selected:
        map_capability = map_capabilities[name]
        requirement_ids = map_capability["requirements"]
        missing_ids = [requirement_id for requirement_id in requirement_ids if requirements[requirement_id]["status"] == "FAIL"]
        result = capabilities.get(name)
        if (
            not isinstance(result, dict)
            or "requirements" not in result
            or "degradable" not in result
            or "fallback" not in result
            or result.get("requirements") != requirement_ids
            or result.get("degradable") != map_capability.get("degradable")
            or result.get("fallback") != map_capability.get("fallback")
            or result.get("missing_requirements") != missing_ids
            or result.get("status") != ("FAIL" if missing_ids else "PASS")
        ):
            return False
        if missing_ids:
            if result["degradable"]:
                expected_fallbacks.append(name)
            else:
                blocking = True
    expected_fallbacks.sort()
    expected_dependency_status = "BLOCKED" if blocking else "DEGRADED" if expected_fallbacks else "PASS"
    if (
        dependency_result.get("fallback_capabilities") != expected_fallbacks
        or dependency_result.get("status") != expected_dependency_status
        or record.get("dependency_status") != expected_dependency_status
    ):
        return False

    expected_fallback_types = [
        item for item in requested_types if FALLBACK_CAPABILITY_BY_ASSET_TYPE[item] in expected_fallbacks
    ]
    expected_modes = {
        item: "source-crop" if item in expected_fallback_types else "editable" for item in requested_types
    }
    if (
        record.get("fallback_asset_types") != expected_fallback_types
        or record.get("available_reconstruction_modes") != expected_modes
    ):
        return False
    return {
        "requested_types": requested_types,
        "dependency_status": expected_dependency_status,
        "fallback_types": expected_fallback_types,
        "modes": expected_modes,
    }


def canonical_preflight_proves_fallback(record: object, asset_type: object, capability_name: object) -> bool:
    """Require the complete PRE-FLIGHT and dependency records to agree with the bundled map."""
    if not isinstance(asset_type, str) or not isinstance(capability_name, str) or not isinstance(record, dict):
        return False
    state = canonical_preflight_dependency_state(record)
    return bool(
        state
        and FALLBACK_CAPABILITY_BY_ASSET_TYPE.get(asset_type) == capability_name
        and record.get("status") == "PASS"
        and state["dependency_status"] == "DEGRADED"
        and asset_type in state["fallback_types"]
        and state["modes"].get(asset_type) == "source-crop"
    )


def validate_fallback_reason(
    asset: dict[str, Any], label: str, uncertainty_ids: set[str], package: Path, errors: list[str]
) -> None:
    reason = asset.get("fallback_reason")
    if reason is None:
        errors.append(f"{label} fallback_reason is required")
        return
    if not isinstance(reason, dict):
        errors.append(f"{label} fallback_reason must be an object with code and machine-verifiable evidence")
        return
    code = reason.get("code")
    if code not in FALLBACK_REASON_CODES:
        errors.append(f"{label} fallback_reason.code must be one of: {', '.join(sorted(FALLBACK_REASON_CODES))}")
    allowed_elements = FALLBACK_AFFECTED_ELEMENTS.get(asset.get("asset_type"), set())
    affected_elements = reason.get("affected_elements")
    if (
        not isinstance(affected_elements, list)
        or not affected_elements
        or any(not isinstance(item, str) or item not in allowed_elements for item in affected_elements)
    ):
        errors.append(f"{label} fallback_reason.affected_elements is required and must list controlled asset elements")
    if code in {"source-uncertainty", "irreproducible-source-detail"}:
        observations = reason.get("observations")
        if not isinstance(observations, list) or not observations:
            errors.append(f"{label} fallback_reason.observations is required")
        else:
            observed_elements: set[str] = set()
            source_bbox = asset.get("source_bbox")
            evidence_options = {asset.get("raw_crop"), asset.get("comparison_evidence")}
            for index, observation in enumerate(observations):
                observation_label = f"{label} fallback_reason.observations[{index}]"
                if not isinstance(observation, dict):
                    errors.append(f"{observation_label} must be an object")
                    continue
                if observation.get("issue_code") not in OBSERVATION_ISSUE_CODES.get(code, set()):
                    errors.append(f"{observation_label}.issue_code is not allowed for fallback_reason.code {code!r}")
                element_type = observation.get("element_type")
                if not isinstance(element_type, str) or element_type not in allowed_elements:
                    errors.append(f"{observation_label}.element_type must be a controlled affected element")
                else:
                    observed_elements.add(element_type)
                if not isinstance(observation.get("element_id"), str) or not observation["element_id"].strip():
                    errors.append(f"{observation_label}.element_id is required")
                if observation.get("page_id") != asset.get("source_page_id"):
                    errors.append(f"{observation_label}.page_id must equal the asset source_page_id")
                bbox = observation.get("bbox")
                if not isinstance(bbox, dict) or any(key not in bbox for key in ("x0", "y0", "x1", "y1")):
                    errors.append(f"{observation_label}.bbox requires x0, y0, x1, and y1")
                elif not all(is_finite_number(bbox[key]) for key in ("x0", "y0", "x1", "y1")):
                    errors.append(f"{observation_label}.bbox coordinates must be finite numbers")
                elif not isinstance(source_bbox, dict) or any(key not in source_bbox for key in ("x0", "y0", "x1", "y1")):
                    errors.append(f"{observation_label}.bbox cannot be bounded because asset source_bbox is invalid")
                elif bbox["x0"] < source_bbox["x0"] or bbox["y0"] < source_bbox["y0"] or bbox["x0"] >= bbox["x1"] or bbox["y0"] >= bbox["y1"] or bbox["x1"] > source_bbox["x1"] or bbox["y1"] > source_bbox["y1"]:
                    errors.append(f"{observation_label}.bbox must be inside the asset raw source bbox")
                if observation.get("evidence_ref") not in evidence_options:
                    errors.append(f"{observation_label}.evidence_ref must reference raw_crop or comparison_evidence")
            if isinstance(affected_elements, list):
                missing_elements = sorted(set(item for item in affected_elements if isinstance(item, str)) - observed_elements)
                if missing_elements:
                    errors.append(f"{label} fallback_reason.observations is missing affected elements: {', '.join(missing_elements)}")
    if code == "source-uncertainty":
        linked_ids = reason.get("uncertainty_ids")
        if not isinstance(linked_ids, list) or not linked_ids or any(not isinstance(item, str) or item not in uncertainty_ids for item in linked_ids):
            errors.append(f"{label} source-uncertainty fallback_reason requires manifest uncertainty_ids")
    if code == "conditional-capability-unavailable":
        expected = FALLBACK_CAPABILITY_BY_ASSET_TYPE.get(asset.get("asset_type"))
        if reason.get("capability") != expected:
            errors.append(f"{label} conditional-capability-unavailable fallback_reason must name capability {expected!r}")
        dependency_ref = reason.get("dependency_evidence_ref")
        if not isinstance(dependency_ref, str) or not dependency_ref.strip():
            errors.append(f"{label} fallback_reason.dependency_evidence_ref is required")
        elif dependency_ref != CANONICAL_PREFLIGHT_EVIDENCE:
            errors.append(f"{label} fallback_reason.dependency_evidence_ref must reference canonical {CANONICAL_PREFLIGHT_EVIDENCE}")
        else:
            relative = Path(dependency_ref)
            if relative.is_absolute() or ".." in relative.parts or not (package / relative).is_file():
                errors.append(f"{label} fallback_reason.dependency_evidence_ref must be the existing canonical PRE-FLIGHT artifact")
            else:
                try:
                    dependency_record = read_json(package / relative)
                except Exception:
                    dependency_record = None
                if not canonical_preflight_proves_fallback(dependency_record, asset.get("asset_type"), expected):
                    errors.append(f"{label} canonical PRE-FLIGHT dependency evidence is incomplete for unavailable capability {expected!r}")


def validate_vector_build_record(
    asset: dict[str, Any],
    label: str,
    reconstruction_source: Path | None,
    rendered_asset: Path | None,
    build_record: Path | None,
    errors: list[str],
) -> None:
    """Bind vector build evidence to the delivered source and rendered PDF by content hash."""
    if build_record is None:
        return
    try:
        record = read_json(build_record)
    except Exception as exc:
        errors.append(f"{label} build_record must be readable JSON: {exc}")
        return
    if record.get("kind") != VECTOR_BUILD_RECORD_KIND:
        errors.append(f"{label} build_record kind must be {VECTOR_BUILD_RECORD_KIND!r}")
    if record.get("schema_version") != VECTOR_BUILD_RECORD_SCHEMA_VERSION:
        errors.append(f"{label} build_record schema_version must be {VECTOR_BUILD_RECORD_SCHEMA_VERSION!r}")
    if record.get("status") != "PASS":
        errors.append(f"{label} build_record status must be PASS")
    if record.get("asset_id") != asset.get("asset_id"):
        errors.append(f"{label} build_record asset_id must match asset_id")

    def require_nonempty_string(field: str) -> None:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label} build_record {field} must be a non-empty string")

    for field in ("engine", "engine_version", "renderer", "renderer_version"):
        require_nonempty_string(field)
    for field in ("stdout_tail", "stderr_tail"):
        if not isinstance(record.get(field), str):
            errors.append(f"{label} build_record {field} must be a string")

    def safe_evidence_path(value: object) -> bool:
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            return False
        posix_path = Path(value)
        windows_path = PureWindowsPath(value)
        if posix_path.is_absolute() or windows_path.is_absolute():
            return True
        return ".." not in posix_path.parts and ".." not in windows_path.parts

    rendered_pages = record.get("rendered_pages")
    if not isinstance(rendered_pages, list) or not rendered_pages or any(not safe_evidence_path(page) for page in rendered_pages):
        errors.append(f"{label} build_record rendered_pages must be a non-empty list of safe evidence paths")

    def validate_record_hash(field: str, artifact: Path | None, source_field: str) -> None:
        recorded = record.get(field)
        if not isinstance(recorded, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", recorded):
            errors.append(f"{label} build_record {field} must be a 64-character SHA-256 hex digest")
        elif artifact is not None and sha256_file(artifact) != recorded.lower():
            errors.append(f"{label} build_record {field} does not match {source_field}")

    validate_record_hash("source_sha256", reconstruction_source, "reconstruction_source")
    validate_record_hash("pdf_sha256", rendered_asset, "rendered_asset")


def validate_visual_assets(manifest: dict[str, Any], package: Path, errors: list[str]) -> None:
    """Validate reconstruction provenance for figure and table asset records."""
    package = package.resolve()
    assets: list[tuple[str, int, dict[str, Any]]] = []
    for collection_name in ("figures", "tables"):
        collection = manifest.get(collection_name, [])
        if not isinstance(collection, list):
            errors.append(f"{collection_name} must be an array")
            continue
        for index, asset in enumerate(collection):
            if not isinstance(asset, dict):
                errors.append(f"{collection_name}[{index}] must be an object")
                continue
            assets.append((collection_name, index, asset))

    asset_id_occurrences: dict[str, list[str]] = {}
    for collection_name, index, asset in assets:
        asset_id = asset.get("asset_id")
        if isinstance(asset_id, str) and asset_id:
            asset_id_occurrences.setdefault(asset_id, []).append(f"{collection_name}[{index}]")
    for asset_id, locations in asset_id_occurrences.items():
        if len(locations) > 1:
            errors.append(f"asset_id values must be globally unique: {asset_id} occurs in {', '.join(locations)}")

    schema_version = manifest.get("schema_version")
    if not isinstance(schema_version, str) or schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        return
    schema_1_1 = schema_version == "1.1"
    if manifest.get("status") == "VERIFIED" and assets and not schema_1_1:
        errors.append("VERIFIED packages with visual assets require manifest schema_version 1.1")
    if not schema_1_1:
        return
    if manifest.get("status") == "BLOCKED":
        return

    pages = manifest.get("pages", [])
    page_by_id = {
        page.get("page_id"): page
        for page in pages
        if isinstance(page, dict) and isinstance(page.get("page_id"), str) and page["page_id"]
    } if isinstance(pages, list) else {}
    questions = manifest.get("questions", [])
    question_by_id = {
        question.get("question_id"): question
        for question in questions
        if isinstance(question, dict) and isinstance(question.get("question_id"), str) and question["question_id"]
    } if isinstance(questions, list) else {}
    uncertainty_ids = {
        item.get("uncertainty_id")
        for item in manifest.get("uncertainties", [])
        if isinstance(item, dict) and isinstance(item.get("uncertainty_id"), str) and item["uncertainty_id"]
    } if isinstance(manifest.get("uncertainties", []), list) else set()
    table_ids = {
        table_id
        for collection_name, _, table in assets
        if collection_name == "tables"
        for table_id in (table.get("asset_id"), table.get("table_id"))
        if isinstance(table_id, str) and table_id
    }
    editable_source_text = read_editable_source(package, errors)

    def escaped_by_odd_backslashes(value: str, position: int) -> bool:
        slash_count = 0
        cursor = position - 1
        while cursor >= 0 and value[cursor] == "\\":
            slash_count += 1
            cursor -= 1
        return slash_count % 2 == 1

    def strip_tex_comments(value: str) -> str:
        uncommented_lines: list[str] = []
        for line in value.splitlines(keepends=True):
            for position, character in enumerate(line):
                if character == "%" and not escaped_by_odd_backslashes(line, position):
                    newline = "\n" if line.endswith("\n") else ""
                    uncommented_lines.append(line[:position] + newline)
                    break
            else:
                uncommented_lines.append(line)
        return "".join(uncommented_lines)

    def has_editable_structured_text_block(block_id: str) -> bool:
        uncommented = strip_tex_comments(editable_source_text)
        marker = re.compile(r"\\ScanExamTextBlock\s*\{\s*" + re.escape(block_id) + r"\s*\}\s*\{")
        for match in marker.finditer(uncommented):
            depth = 1
            position = match.end()
            content_start = position
            while position < len(uncommented) and depth:
                character = uncommented[position]
                if character == "{" and not escaped_by_odd_backslashes(uncommented, position):
                    depth += 1
                elif character == "}" and not escaped_by_odd_backslashes(uncommented, position):
                    depth -= 1
                position += 1
            if depth == 0 and uncommented[content_start:position - 1].strip():
                return True
        return False

    def label_for(collection_name: str, index: int, asset: dict[str, Any]) -> str:
        asset_id = asset.get("asset_id")
        return f"{collection_name}[{index}] ({asset_id})" if isinstance(asset_id, str) and asset_id else f"{collection_name}[{index}]"

    def require_string(asset: dict[str, Any], label: str, field: str) -> str | None:
        value = asset.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label} {field} is required")
            return None
        return value

    def artifact_path(asset: dict[str, Any], label: str, field: str) -> Path | None:
        value = require_string(asset, label, field)
        if value is None:
            return None
        relative = Path(value)
        if relative.is_absolute():
            errors.append(f"{label} {field} must be package-relative")
            return None
        if ".." in relative.parts:
            errors.append(f"{label} {field} must not contain '..' traversal")
            return None
        resolved = (package / relative).resolve()
        try:
            resolved.relative_to(package)
        except ValueError:
            errors.append(f"{label} {field} must resolve beneath package")
            return None
        if not resolved.is_file():
            errors.append(f"{label} {field} does not exist: {value}")
            return None
        return resolved

    def validate_hash(asset: dict[str, Any], label: str, field: str, path: Path | None) -> None:
        hash_field = f"{field}_sha256"
        recorded = require_string(asset, label, hash_field)
        if recorded is None:
            return
        if not re.fullmatch(r"[0-9a-fA-F]{64}", recorded):
            errors.append(f"{label} {hash_field} must be a 64-character SHA-256 hex digest")
            return
        if path is not None and sha256_file(path) != recorded.lower():
            errors.append(f"{label} {hash_field} does not match {field}")

    for collection_name, index, asset in assets:
        label = label_for(collection_name, index, asset)
        for field in ("asset_id", "asset_type"):
            require_string(asset, label, field)
        question_id = require_string(asset, label, "question_id")
        if question_id is not None and question_id not in question_by_id:
            errors.append(f"{label} question_id does not identify a manifest question: {question_id}")
        source_page_id = require_string(asset, label, "source_page_id")
        if source_page_id is not None and source_page_id not in page_by_id:
            errors.append(f"{label} source_page_id does not identify a manifest page: {source_page_id}")

        bbox = asset.get("source_bbox")
        if not isinstance(bbox, dict) or any(key not in bbox for key in ("x0", "y0", "x1", "y1")):
            errors.append(f"{label} source_bbox requires x0, y0, x1, and y1")
        elif any(not isinstance(bbox[key], (int, float)) or isinstance(bbox[key], bool) or not math.isfinite(bbox[key]) for key in ("x0", "y0", "x1", "y1")):
            errors.append(f"{label} source_bbox coordinates must be finite numbers")
        elif bbox["x0"] < 0 or bbox["y0"] < 0 or bbox["x0"] >= bbox["x1"] or bbox["y0"] >= bbox["y1"]:
            errors.append(f"{label} source_bbox must use non-negative x0<x1 and y0<y1 raster coordinates")
        elif source_page_id in page_by_id:
            page = page_by_id[source_page_id]
            width = page.get("page_width_px")
            height = page.get("page_height_px")
            if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0 for value in (width, height)):
                errors.append(f"{label} referenced source page must declare finite positive page_width_px and page_height_px")
            elif bbox["x1"] > width or bbox["y1"] > height:
                errors.append(f"{label} source_bbox exceeds source page dimensions")

        raw_crop = artifact_path(asset, label, "raw_crop")
        validate_hash(asset, label, "raw_crop", raw_crop)

        validate_element_checklist(asset, label, errors)
        artifact_path(asset, label, "comparison_evidence")
        if asset.get("qa_status") != "PASS":
            errors.append(f"{label} qa_status must be PASS")
        require_string(asset, label, "decision_reason")

        mode = asset.get("reproduction_mode")
        if mode not in {"structured-text", "vector-redraw", "source-crop"}:
            errors.append(f"{label} reproduction_mode must be structured-text, vector-redraw, or source-crop")
            continue

        if mode == "vector-redraw":
            reconstruction_source = artifact_path(asset, label, "reconstruction_source")
            rendered_asset = artifact_path(asset, label, "rendered_asset")
            validate_hash(asset, label, "rendered_asset", rendered_asset)
            build_record = artifact_path(asset, label, "build_record")
            validate_vector_build_record(asset, label, reconstruction_source, rendered_asset, build_record, errors)
            toolchain = asset.get("toolchain")
            if not isinstance(toolchain, dict) or not toolchain:
                errors.append(f"{label} toolchain is required and must be a non-empty object")
        elif mode == "source-crop":
            validate_fallback_reason(asset, label, uncertainty_ids, package, errors)
        else:
            table_id = require_string(asset, label, "table_id")
            if table_id is not None and table_id not in table_ids:
                errors.append(f"{label} table_id does not identify a manifest table: {table_id}")
            text_block_ids = asset.get("text_block_ids")
            if not isinstance(text_block_ids, list) or not text_block_ids or any(not isinstance(item, str) or not item.strip() for item in text_block_ids):
                errors.append(f"{label} text_block_ids is required and must contain real-text block IDs")
                continue
            question = question_by_id.get(question_id)
            linked_block_ids = question.get("content_block_ids", []) if isinstance(question, dict) else []
            if not isinstance(linked_block_ids, list):
                linked_block_ids = []
            for block_id in text_block_ids:
                if block_id not in linked_block_ids:
                    errors.append(f"{label} text_block_id {block_id!r} is not linked to question {question_id}")
                if not has_editable_structured_text_block(block_id):
                    errors.append(f"{label} text_block_id {block_id!r} is not present in editable source exam.tex or has no non-comment ScanExamTextBlock")


def visual_asset_ids(manifest: dict[str, Any]) -> set[str]:
    return {
        asset["asset_id"]
        for collection_name in ("figures", "tables")
        for asset in manifest.get(collection_name, [])
        if isinstance(asset, dict) and isinstance(asset.get("asset_id"), str) and asset["asset_id"]
    }


def validate_empty_visual_inventory(manifest: dict[str, Any], package: Path, evidence: list[str], errors: list[str]) -> None:
    inventory_ref = "audit/visual-inventory.json"
    if inventory_ref not in evidence:
        errors.append("visual-assets fresh pass with no visual assets must reference audit/visual-inventory.json")
        return
    inventory_path = package / inventory_ref
    try:
        inventory = read_json(inventory_path)
    except Exception:
        inventory = None
    if not isinstance(inventory, dict):
        errors.append("visual inventory evidence must be a readable JSON object")
        return
    if inventory.get("kind") != "visual-inventory" or inventory.get("version") != 1 or inventory.get("status") != "COMPLETE":
        errors.append("visual inventory evidence must declare kind=visual-inventory, version=1, and status=COMPLETE")
    if inventory.get("asset_count") != 0:
        errors.append("visual inventory evidence asset_count must be 0")
    manifest_pages = manifest.get("pages", [])
    if not isinstance(manifest_pages, list) or not manifest_pages:
        errors.append("manifest pages for visual inventory must be a non-empty array")
        return
    expected_rows: list[tuple[str, str]] = []
    for page in manifest_pages:
        if not isinstance(page, dict) or set(page) < {"page_id", "derived_page_sha256"}:
            errors.append("manifest pages for visual inventory must each have non-empty page_id and derived_page_sha256")
            return
        page_id = page.get("page_id")
        page_hash = page.get("derived_page_sha256")
        if not isinstance(page_id, str) or not page_id or not isinstance(page_hash, str) or not page_hash:
            errors.append("manifest pages for visual inventory must each have non-empty page_id and derived_page_sha256")
            return
        expected_rows.append((page_id, page_hash))
    if len({page_id for page_id, _ in expected_rows}) != len(expected_rows):
        errors.append("manifest pages for visual inventory must not duplicate page_id values")
        return
    reviewed_pages = inventory.get("reviewed_source_pages")
    if not isinstance(reviewed_pages, list) or not reviewed_pages:
        errors.append("visual inventory evidence requires non-empty reviewed_source_pages")
        return
    expected_ids = {page_id for page_id, _ in expected_rows}
    exact_rows = len(expected_rows) == len(expected_ids) and bool(expected_rows) and len(reviewed_pages) == len(expected_rows)
    seen_ids: set[str] = set()
    reviewed_rows: set[tuple[str, str]] = set()
    for row in reviewed_pages:
        if not isinstance(row, dict) or set(row) != {"page_id", "derived_page_sha256"}:
            exact_rows = False
            continue
        page_id = row.get("page_id")
        page_hash = row.get("derived_page_sha256")
        if not isinstance(page_id, str) or not page_id or not isinstance(page_hash, str) or not page_hash:
            exact_rows = False
            continue
        if page_id in seen_ids:
            exact_rows = False
        seen_ids.add(page_id)
        reviewed_rows.add((page_id, page_hash))
    if not exact_rows or seen_ids != expected_ids or reviewed_rows != set(expected_rows):
        errors.append("visual inventory evidence reviewed_source_pages must contain exactly one valid row per manifest page")


def validate_fresh_passes(manifest: dict[str, Any], package: Path, errors: list[str]) -> None:
    fresh = manifest.get("fresh_passes")
    schema_version = manifest.get("schema_version")
    if not isinstance(schema_version, str) or schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        return
    schema_1_1 = schema_version == "1.1"
    required_passes = SCHEMA_1_1_FRESH_PASSES if schema_1_1 else LEGACY_FRESH_PASSES
    if not isinstance(fresh, dict):
        errors.append("VERIFIED requires four fresh passes")
        return
    for name in required_passes:
        item = fresh.get(name)
        if not isinstance(item, dict) or item.get("completed") is not True or item.get("source_reopened") is not True:
            errors.append(f"fresh pass {name} must be completed with source_reopened=true")
    if not schema_1_1:
        return

    visual = fresh.get("visual-assets")
    if not isinstance(visual, dict) or visual.get("completed") is not True or visual.get("source_reopened") is not True:
        return
    scope = visual.get("review_scope")
    if not isinstance(scope, str) or not scope.strip():
        errors.append("visual-assets fresh pass requires a non-empty review_scope")
    expected_ids = visual_asset_ids(manifest)
    expected_outcome = "assets-reviewed" if expected_ids else "no-visual-assets"
    if visual.get("inventory_outcome") != expected_outcome:
        errors.append(f"visual-assets fresh pass inventory_outcome must be {expected_outcome!r}")
    reviewed_ids = visual.get("reviewed_asset_ids")
    if not isinstance(reviewed_ids, list) or any(not isinstance(item, str) or not item for item in reviewed_ids):
        errors.append("visual-assets fresh pass requires reviewed_asset_ids")
    else:
        if len(set(reviewed_ids)) != len(reviewed_ids):
            errors.append("visual-assets fresh pass reviewed_asset_ids must not contain duplicates")
        missing_ids = sorted(expected_ids - set(reviewed_ids))
        if missing_ids:
            errors.append(f"visual-assets fresh pass is missing reviewed asset IDs: {', '.join(missing_ids)}")
        if not expected_ids and reviewed_ids:
            errors.append("visual-assets fresh pass with no visual assets must have an empty reviewed_asset_ids list")
    evidence = visual.get("evidence")
    if not isinstance(evidence, list) or not evidence or any(not isinstance(item, str) or not item.strip() for item in evidence):
        errors.append("visual-assets fresh pass requires non-empty evidence paths")
    else:
        for index, value in enumerate(evidence):
            relative = Path(value)
            if relative.is_absolute() or ".." in relative.parts:
                errors.append(f"visual-assets fresh pass evidence[{index}] must be a package-relative path")
                continue
            if not (package / relative).is_file():
                errors.append(f"visual-assets fresh pass evidence[{index}] does not exist: {value}")
        if not expected_ids:
            validate_empty_visual_inventory(manifest, package, evidence, errors)


def main() -> int:
    args = parse_args()
    package = args.package_dir.resolve()
    audit_dir = package / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    validation_path = audit_dir / "validation.json"
    errors: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, object] = {}

    required = {
        "pdf": package / "exam-digital.pdf",
        "source": package / "exam.tex",
        "figures": package / "figures",
        "manifest": package / "manifest.json",
        "report": package / "check-report.md",
    }
    for name in ("manifest", "report"):
        path = required[name]
        if not path.exists():
            errors.append(f"required artifact missing: {name} ({path.name})")

    manifest: dict[str, Any] = {}
    if required["manifest"].exists():
        try:
            manifest = read_json(required["manifest"])
        except Exception as exc:
            errors.append(f"manifest cannot be read: {exc}")
    status = manifest.get("status")
    if not isinstance(status, str) or status not in ALLOWED_STATUSES:
        errors.append("manifest status must be BLOCKED, DRAFT-UNVERIFIED, or VERIFIED")
    schema_version = manifest.get("schema_version")
    if not isinstance(schema_version, str) or schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append("manifest schema_version must be 1.0 or 1.1")
    source_files = manifest.get("source_files")
    if not isinstance(source_files, list) or not source_files:
        errors.append("manifest must retain at least one frozen source file record")

    if status == "BLOCKED":
        preflight_path = package / "audit" / "preflight.json"
        if not preflight_path.exists():
            errors.append("BLOCKED package requires audit/preflight.json")
        else:
            try:
                preflight = read_json(preflight_path)
                if not canonical_blocked_preflight(preflight, manifest):
                    errors.append("BLOCKED package requires canonical BLOCKED PRE-FLIGHT evidence")
                evidence["preflight"] = str(preflight_path)
            except Exception as exc:
                errors.append(f"PRE-FLIGHT evidence cannot be read: {exc}")
    else:
        for name in ("pdf", "source", "figures"):
            path = required[name]
            if not path.exists():
                errors.append(f"required artifact missing: {name} ({path.name})")

    if required["source"].exists():
        read_editable_source(package, errors)

    report_text = ""
    if required["report"].exists():
        report_text = required["report"].read_text(encoding="utf-8")
        if isinstance(schema_version, str) and schema_version in SUPPORTED_SCHEMA_VERSIONS:
            report_headings = SCHEMA_1_1_REPORT_HEADINGS if schema_version == "1.1" else LEGACY_REPORT_HEADINGS
            missing_headings = [heading for heading in report_headings if heading not in report_text]
            if missing_headings:
                errors.append(f"check report missing sections: {', '.join(missing_headings)}")
        found_status = report_status(report_text)
        if found_status != status:
            errors.append(f"report status {found_status!r} does not match manifest status {status!r}")

    uncertainties = manifest.get("uncertainties", [])
    if not isinstance(uncertainties, list):
        errors.append("uncertainties must be an array")
        uncertainties = []
    unresolved = [
        item for item in uncertainties
        if isinstance(item, dict) and item.get("status") != "resolved"
    ]
    if status == "VERIFIED" and unresolved:
        errors.append("VERIFIED cannot contain unresolved uncertainties")
    validate_revision_history(manifest, errors)
    validate_visual_assets(manifest, package, errors)

    if status == "VERIFIED":
        validate_fresh_passes(manifest, package, errors)
        consistency = manifest.get("final_consistency")
        if not isinstance(consistency, dict):
            errors.append("VERIFIED requires final consistency answers 1 through 10")
        else:
            for number in range(1, 11):
                value = consistency.get(str(number))
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.append(f"final consistency answer {number} is missing")

    extracted = ""
    if status != "BLOCKED" and required["pdf"].exists():
        try:
            extracted = extract_pdf_text(required["pdf"])
            if not extracted.strip():
                errors.append("PDF has no extractable text layer")
            for anchor in manifest.get("required_text_anchors", []):
                if not isinstance(anchor, str) or anchor not in extracted:
                    errors.append(f"PDF text layer missing required anchor: {anchor!r}")
            evidence["pdf_sha256"] = sha256_file(required["pdf"])
            evidence["extracted_character_count"] = len(extracted)
        except Exception as exc:
            errors.append(f"PDF text extraction failed: {exc}")

    pages = manifest.get("pages", [])
    if status != "BLOCKED" and isinstance(pages, list) and pages:
        try:
            from pypdf import PdfReader

            output_page_count = len(PdfReader(str(required["pdf"])).pages)
            evidence["source_page_count"] = len(pages)
            evidence["output_page_count"] = output_page_count
            if len(pages) != output_page_count:
                errors.append(f"page count mismatch: source {len(pages)}, output {output_page_count}")
        except Exception as exc:
            errors.append(f"unable to compare page counts: {exc}")

    result = {
        "schema_version": "1.0",
        "status": "PASS" if not errors else "FAIL",
        "validated_at": now_iso(),
        "package_dir": str(package),
        "manifest_status": status,
        "errors": errors,
        "warnings": warnings,
        "evidence": evidence,
        "verified_definition": "Required source-file comparison checks were executed and passed; this is not an absolute zero-error guarantee.",
    }
    write_json(validation_path, result)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    print(str(validation_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
