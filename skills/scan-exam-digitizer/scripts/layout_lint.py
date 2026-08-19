from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

from _common import now_iso, read_json, write_json


REPORT_KIND = "scan-exam-digitizer-layout-lint"
REPORT_SCHEMA_VERSION = "1.0"
MIN_GAP_PT = 2.0
MIN_CELL_PADDING_PT = 3.0
MIN_ROW_HEIGHT_PT = 14.0
MIN_FONT_SIZE_PT = 8.5
MIN_WIDTH_FRACTION = 0.65
MAX_WIDTH_FRACTION = 0.92
TEXT_KINDS = {"label", "text", "value", "unit"}
OBSTACLE_KINDS = TEXT_KINDS | {"wire", "border"}
FIGURE_ASSET_TYPES = {"block-diagram", "signal-flow", "circuit", "plot-waveform"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint declared layout contracts for visual exam assets.")
    parser.add_argument("--package-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def rectangle(value: object, label: str, errors: list[str]) -> tuple[float, float, float, float] | None:
    if not isinstance(value, dict) or any(key not in value for key in ("x0", "y0", "x1", "y1")):
        errors.append(f"{label} must contain x0, y0, x1, and y1")
        return None
    coordinates = tuple(value[key] for key in ("x0", "y0", "x1", "y1"))
    if any(not is_number(item) for item in coordinates):
        errors.append(f"{label} coordinates must be finite numbers")
        return None
    x0, y0, x1, y1 = (float(item) for item in coordinates)
    if not x0 < x1 or not y0 < y1:
        errors.append(f"{label} must satisfy x0<x1 and y0<y1")
        return None
    return x0, y0, x1, y1


def contains(outer: tuple[float, float, float, float], inner: tuple[float, float, float, float]) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def gap(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
    horizontal = max(first[0] - second[2], second[0] - first[2], 0.0)
    vertical = max(first[1] - second[3], second[1] - first[3], 0.0)
    return math.hypot(horizontal, vertical)


def check_width_fraction(layout: dict[str, Any], slot: tuple[float, float, float, float], label: str, errors: list[str]) -> None:
    fraction_key = "table_width_fraction" if layout.get("asset_type") == "table" else "figure_width_fraction"
    fraction = layout.get(fraction_key)
    if not is_number(fraction):
        errors.append(f"{label} {fraction_key} is required")
        return
    if not MIN_WIDTH_FRACTION <= float(fraction) <= MAX_WIDTH_FRACTION:
        errors.append(f"{label} {fraction_key} must be between {MIN_WIDTH_FRACTION:.2f} and {MAX_WIDTH_FRACTION:.2f}")
    page_width = float(layout["page_width_pt"])
    derived = (slot[2] - slot[0]) / page_width
    if abs(float(fraction) - derived) > 0.02:
        errors.append(f"{label} {fraction_key} does not match the slot/page width ratio")


def check_common_layout(layout: object, label: str, errors: list[str]) -> tuple[dict[str, Any], tuple[float, float, float, float]] | None:
    if not isinstance(layout, dict):
        errors.append(f"{label} layout is required")
        return None
    for field in ("page_width_pt", "page_height_pt", "font_size_pt"):
        if not is_number(layout.get(field)) or float(layout[field]) <= 0:
            errors.append(f"{label} layout.{field} must be a positive number")
    if is_number(layout.get("font_size_pt")) and float(layout["font_size_pt"]) < MIN_FONT_SIZE_PT:
        errors.append(f"{label} font_size_pt must be at least {MIN_FONT_SIZE_PT:g} pt")
    if not is_number(layout.get("page_width_pt")) or not is_number(layout.get("page_height_pt")):
        return layout, (0.0, 0.0, 0.0, 0.0)
    page = (0.0, 0.0, float(layout["page_width_pt"]), float(layout["page_height_pt"]))
    slot = rectangle(layout.get("slot"), f"{label} layout.slot", errors)
    if slot is None:
        return layout, page
    if not contains(page, slot):
        errors.append(f"{label} layout.slot is outside the page box")
    check_width_fraction(layout, slot, label, errors)
    return layout, slot


def lint_figure(layout: dict[str, Any], slot: tuple[float, float, float, float], label: str, errors: list[str]) -> None:
    elements = layout.get("elements")
    if not isinstance(elements, list) or not elements:
        errors.append(f"{label} layout.elements must be a non-empty list")
        return
    parsed: list[tuple[str, str, tuple[float, float, float, float]]] = []
    seen: set[str] = set()
    for index, element in enumerate(elements):
        element_label = f"{label} layout.elements[{index}]"
        if not isinstance(element, dict):
            errors.append(f"{element_label} must be an object")
            continue
        element_id = element.get("id")
        kind = element.get("kind")
        if not isinstance(element_id, str) or not element_id.strip():
            errors.append(f"{element_label}.id must be a non-empty string")
            continue
        if element_id in seen:
            errors.append(f"{label} layout element ID is duplicated: {element_id}")
            continue
        seen.add(element_id)
        if not isinstance(kind, str) or kind not in {"label", "text", "value", "unit", "wire", "border", "shape", "node", "curve", "arrow", "axis", "point"}:
            errors.append(f"{element_label}.kind is not a supported layout element kind")
            continue
        bbox = rectangle(element.get("bbox"), f"{element_label}.bbox", errors)
        if bbox is None:
            continue
        if not contains(slot, bbox):
            errors.append(f"{element_label} is outside the figure slot")
        parsed.append((element_id, kind, bbox))

    for index, (first_id, first_kind, first_bbox) in enumerate(parsed):
        for second_id, second_kind, second_bbox in parsed[index + 1 :]:
            if not ((first_kind in TEXT_KINDS and second_kind in OBSTACLE_KINDS) or (second_kind in TEXT_KINDS and first_kind in OBSTACLE_KINDS)):
                continue
            distance = gap(first_bbox, second_bbox)
            if distance < MIN_GAP_PT:
                errors.append(
                    f"{label} label/wire collision or insufficient gap: "
                    f"{first_id} ({first_kind}) and {second_id} ({second_kind}) are {distance:.2f} pt apart"
                )


def lint_table(layout: dict[str, Any], label: str, errors: list[str]) -> None:
    padding = layout.get("cell_padding_pt")
    if not is_number(padding) or float(padding) < MIN_CELL_PADDING_PT:
        errors.append(f"{label} cell_padding_pt must be at least {MIN_CELL_PADDING_PT:g} pt")
    heights = layout.get("row_heights_pt")
    if not isinstance(heights, list) or not heights:
        errors.append(f"{label} row_heights_pt must be a non-empty list")
    elif any(not is_number(value) or float(value) < MIN_ROW_HEIGHT_PT for value in heights):
        errors.append(f"{label} every row height must be at least {MIN_ROW_HEIGHT_PT:g} pt")


def lint_asset(asset: object, index: int, collection: str, errors: list[str], metrics: dict[str, Any]) -> str | None:
    label = f"{collection}[{index}]"
    if not isinstance(asset, dict):
        errors.append(f"{label} must be an object")
        return None
    asset_id = asset.get("asset_id")
    if not isinstance(asset_id, str) or not asset_id.strip():
        errors.append(f"{label}.asset_id must be a non-empty string")
        return None
    layout = dict(asset.get("layout")) if isinstance(asset.get("layout"), dict) else asset.get("layout")
    if isinstance(layout, dict):
        layout["asset_type"] = asset.get("asset_type")
    result = check_common_layout(layout, f"{label} ({asset_id})", errors)
    if result is None:
        return asset_id
    layout, slot = result
    if asset.get("asset_type") == "table":
        lint_table(layout, f"{label} ({asset_id})", errors)
    elif asset.get("asset_type") in FIGURE_ASSET_TYPES:
        lint_figure(layout, slot, f"{label} ({asset_id})", errors)
    else:
        errors.append(f"{label} ({asset_id}) has an unsupported asset_type")
    metrics[asset_id] = {
        "asset_type": asset.get("asset_type"),
        "font_size_pt": layout.get("font_size_pt"),
        "slot": layout.get("slot"),
    }
    return asset_id


def lint_package(package: Path, output: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = package / "manifest.json"
    manifest: dict[str, Any] = {}
    try:
        manifest = read_json(manifest_path)
    except Exception as exc:
        errors.append(f"manifest cannot be read: {exc}")

    assets: list[tuple[str, object]] = []
    for collection in ("figures", "tables"):
        values = manifest.get(collection, [])
        if not isinstance(values, list):
            errors.append(f"manifest {collection} must be an array")
            continue
        assets.extend((collection, asset) for asset in values)

    metrics: dict[str, Any] = {}
    checked_ids: list[str] = []
    for index, (collection, asset) in enumerate(assets):
        asset_id = lint_asset(asset, index, collection, errors, metrics)
        if asset_id is not None:
            checked_ids.append(asset_id)
    if len(set(checked_ids)) != len(checked_ids):
        errors.append("layout asset IDs must be globally unique")

    result: dict[str, Any] = {
        "kind": REPORT_KIND,
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": "PASS" if not errors else "FAIL",
        "generated_at": now_iso(),
        "package_dir": str(package),
        "checked_asset_ids": checked_ids,
        "metrics": metrics,
        "warnings": warnings,
        "errors": errors,
    }
    output_path = output or package / "audit" / "layout-lint.json"
    write_json(output_path, result)
    return result


def main() -> int:
    args = parse_args()
    result = lint_package(args.package_dir.resolve(), args.output.resolve() if args.output else None)
    output = args.output.resolve() if args.output else args.package_dir.resolve() / "audit" / "layout-lint.json"
    if result["status"] != "PASS":
        for error in result["errors"]:
            print(error, file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
