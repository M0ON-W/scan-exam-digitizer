# Manifest contract

Use UTF-8 JSON. Preserve stable IDs and append-only revision history. Paths should be package-relative when the artifact is destined for delivery.

For every package state that includes `exam.tex`, the editable source must be decodable UTF-8. Invalid or unreadable source is a normal delivery validation error, including for legacy schema 1.0 drafts; it must not cause a validator traceback.

A `BLOCKED` stop package may omit `exam.tex`, the final PDF, figures, and fresh-pass records only when its manifest and report both say `BLOCKED` and `audit/preflight.json` is canonical blocking evidence: `kind: "scan-exam-digitizer-preflight"`, schema `1.0`, `status: "BLOCKED"`, frozen-input hashes matching the manifest, the controlled PRE-FLIGHT capability set with typed evidence, and the complete dependency-map-bound closure/probes. The exemption requires that the nested dependency result independently derives `BLOCKED` from a non-degradable/base requirement failure; a capability-only operational failure (including `latex_compile`) remains a blocked workflow state but cannot justify a validator-PASS minimal stop package. `DRAFT-UNVERIFIED` and `VERIFIED` packages still require the editable source and their normal downstream gates. This exemption does not relax visual-asset provenance for non-`BLOCKED` packages.

## Schema 1.1 visual-asset provenance

Schema `1.1` adds reconstruction provenance for every visual record in both `figures` and `tables`. A future `VERIFIED` package that has at least one such record must declare `"schema_version": "1.1"`. During the transition, a package with no visual records may retain the minimal `1.0` structure, and legacy `DRAFT-UNVERIFIED` 1.0 packages remain accepted unchanged. A draft must adopt 1.1 before it can be promoted to `VERIFIED` with visual records.

Every path below is a non-empty, package-relative file path. Absolute paths, `..` traversal, and symlink targets outside the package are invalid. The validator resolves each path beneath the package and checks that it exists. Required `raw_crop_sha256` and `rendered_asset_sha256` values are lowercase or uppercase 64-hex digests and must match the referenced bytes.

Each entry in `figures` or `tables` is a visual asset. It requires these shared fields:

```json
{
  "asset_id": "A-Q2-01",
  "question_id": "Q2",
  "asset_type": "block-diagram",
  "reproduction_mode": "vector-redraw",
  "source_page_id": "p001",
  "source_bbox": {"x0": 10, "y0": 20, "x1": 200, "y1": 140},
  "raw_crop": "figures/A-Q2-01-raw.png",
  "raw_crop_sha256": "64 hex",
  "element_checklist": {
    "nodes": 2,
    "connections": 1,
    "directions_checked": true,
    "labels_checked": true,
    "values_units_checked": true,
    "orientation_checked": true
  },
  "comparison_evidence": "comparisons/A-Q2-01-side-by-side.png",
  "qa_status": "PASS",
  "decision_reason": "All semantic elements are visually confirmable."
}
```

`source_page_id` and `question_id` must identify records in `pages` and `questions`, respectively. `raw_crop` is mandatory even when an asset is reconstructed: it is the immutable audit evidence for the original scanned region. `comparison_evidence` is the visual source/output comparison reviewed in image QA. `qa_status` is `PASS` only after that review. `decision_reason` records why the selected mode remains faithful; it does not substitute for source evidence.

### Controlled reproduction modes

- `vector-redraw` requires `reconstruction_source`, `rendered_asset`, `rendered_asset_sha256`, `build_record`, and a non-empty `toolchain` object, in addition to every shared field. The reconstruction source, rendered output, and build record must each exist. `build_record` is controlled evidence emitted by `scripts/render_vector_asset.py`: `kind: "scan-exam-digitizer-vector-build"`, schema `1.0`, `status: "PASS"`, the same `asset_id`, SHA-256 values matching `reconstruction_source` and `rendered_asset`, non-empty engine/renderer names and versions, non-empty rendered-page evidence, and string output tails. The validator treats these hashes as authoritative, so recorded original source/output paths need not still exist after the package is moved. Use only when the controlled reconstruction is permitted by the task's fidelity rules; the raw crop and side-by-side comparison remain mandatory.
- `source-crop` requires a structured `fallback_reason`, so the fallback is machine-auditable rather than a vague prose label. It has a controlled `code`, controlled affected elements, and per-element observations anchored to source coordinates and evidence. The raw crop is the delivered visual and must have its matching `raw_crop_sha256`; it still requires the shared checklist and comparison evidence.

  ```json
  {
    "code": "irreproducible-source-detail",
    "affected_elements": ["shading", "hand-drawn-trace"],
    "observations": [{
      "issue_code": "shaded-trace",
      "element_type": "shading",
      "element_id": "curve-fill-1",
      "page_id": "p001",
      "bbox": {"x0": 110, "y0": 220, "x1": 220, "y1": 290},
      "evidence_ref": "figures/A-Q3-01-raw.png"
    }, {
      "issue_code": "freehand-trace",
      "element_type": "hand-drawn-trace",
      "element_id": "trace-1",
      "page_id": "p001",
      "bbox": {"x0": 120, "y0": 225, "x1": 210, "y1": 285},
      "evidence_ref": "figures/A-Q3-01-raw.png"
    }]
  }
  ```

  `code` is exactly one of: `source-uncertainty`, `irreproducible-source-detail`, or `conditional-capability-unavailable`. Every reason has non-empty `affected_elements` from the controlled list for its `asset_type`. `source-uncertainty` and `irreproducible-source-detail` require `observations`: every affected element has at least one record with an allowed `issue_code`, matching `element_type`, non-empty `element_id`, asset `source_page_id`, finite bbox inside the asset source bbox/raw-crop region, and `evidence_ref` equal to `raw_crop` or `comparison_evidence`. Generic prose alone is not evidence. `source-uncertainty` also has non-empty `uncertainty_ids` that identify manifest uncertainty records. `conditional-capability-unavailable` instead has the exact mapped `capability` and `dependency_evidence_ref: "audit/preflight.json"`. This is the canonical PRE-FLIGHT artifact, not an arbitrary `DEGRADED` JSON file: it must declare `kind: "scan-exam-digitizer-preflight"`, `schema_version: "1.0"`, `status: "PASS"`, `dependency_status: "DEGRADED"`, include the affected asset type in `requested_asset_types` and `fallback_asset_types`, route it to `source-crop`, and retain `dependency_result`. The nested record is exactly a `scan-exam-digitizer-dependency-report` schema `1.0` tied by `dependency_map_sha256` to bundled `assets/dependencies.json`. The affected capability and every requested capability must exist in that map; its requirement IDs, degradable flag, probe ID/type/install hint, and type-specific declaration must match the map. Missing IDs exactly match failed probes, and each failed probe has `evidence: null` plus a non-empty note. This proves internally consistent recorded evidence, not unforgeable runtime truth; retain installation/recheck and fresh visual QA evidence.
- `structured-text` requires non-empty `table_id` and `text_block_ids` fields. `table_id` must identify a record in `tables`; `text_block_ids` is a non-empty array of stable IDs for the real editable text/formula blocks. Every block ID must be listed in the linked question's `content_block_ids` and have a non-comment marker with non-empty editable content in `exam.tex`:

  ```latex
  \newcommand{\ScanExamTextBlock}[2]{#2}
  \ScanExamTextBlock{B-Q4-01}{\(R_1 = \frac{U}{I}\)}
  ```

  The marker declaration may be placed in the preamble; every call is the machine-detectable evidence that its second argument is real, editable table/text/formula content. A commented-out marker, bare ID string, or empty second argument fails validation. This is syntactic provenance evidence only: fresh-pass QA must still verify that the editable content faithfully represents the scanned cells. It still keeps a raw scanned crop, hash, checklist, and comparison evidence for audit.

`reproduction_mode` is exactly one of `structured-text`, `vector-redraw`, or `source-crop`; do not introduce free-form modes.

`asset_id` values are globally unique across both `figures` and `tables`. Do not reuse a figure ID for a table or vice versa.

### Element checklists

`asset_type` is exactly `table`, `block-diagram`, `signal-flow`, `circuit`, or `plot-waveform`. Its `element_checklist` uses the required typed keys below: count fields are finite non-negative integers and `*_checked` fields are booleans. A generic object such as `{"x": true}` is invalid. Record `false` only when the item is visibly inapplicable; it is not permission to infer unreadable content.

| Asset type | Required count fields | Required review fields |
| --- | --- | --- |
| `table` | `rows`, `columns` | `headers_checked`, `merged_cells_checked`, `formulas_units_checked`, `cells_checked` |
| `block-diagram`, `signal-flow` | `nodes`, `connections` | `directions_checked`, `labels_checked`, `values_units_checked`, `orientation_checked` |
| `circuit` | `components`, `connections` | `directions_checked`, `labels_checked`, `values_units_checked`, `orientation_checked` |
| `plot-waveform` | `curves` | `axes_checked`, `scale_ticks_checked`, `arrows_checked`, `labels_checked`, `values_units_checked`, `orientation_checked` |

## Coordinate system

Every `source_bbox` uses source-page raster coordinates:

- `coordinate_system`: `pixel`
- `origin`: `top-left`
- `x0`, `y0`: inclusive upper-left edge
- `x1`, `y1`: exclusive lower-right edge
- constraints: `0 <= x0 < x1 <= page_width_px` and `0 <= y0 < y1 <= page_height_px`

All four coordinates and the referenced page dimensions must be finite numeric values. The validator resolves `source_page_id` to its page record and rejects a box that exceeds that page's authoritative `page_width_px` or `page_height_px`. Record those dimensions, `work_dpi`, the original source-file SHA-256, and the derived page-image SHA-256. Do not reuse a bbox after rerendering at a different DPI without recalculating it.

## Required top-level fields

```json
{
  "schema_version": "1.1",
  "status": "DRAFT-UNVERIFIED",
  "created_at": "ISO-8601 timestamp",
  "source_files": [{"path": "source.pdf", "sha256": "64 hex"}],
  "work_dpi": 300,
  "pages": [],
  "questions": [],
  "figures": [],
  "tables": [],
  "uncertainties": [],
  "revision_history": [],
  "fresh_passes": {},
  "required_text_anchors": [],
  "final_consistency": {}
}
```

Each page records `page_id`, logical order, source path/index, `source_file_sha256`, `derived_page_path`, `derived_page_sha256`, pixel width/height, DPI, rotation/orientation review, clipping/legibility review, and any `duplicate_candidate_of`. A duplicate candidate is not permission to remove a page.

Each question records stable ID, displayed number, parent/child relation, page IDs, score if printed, content block IDs, and linked figure/table IDs. Use this to prevent question/figure reassignment.

## Uncertainty entry

```json
{
  "uncertainty_id": "U-001",
  "status": "unresolved",
  "page_id": "p001",
  "question_id": "Q1-2",
  "location": "积分上限",
  "source_bbox": {"x0": 100, "y0": 220, "x1": 180, "y1": 270},
  "page_width_px": 2480,
  "page_height_px": 3508,
  "work_dpi": 300,
  "source_file_sha256": "64 hex",
  "derived_page_sha256": "64 hex",
  "source_crop": "uncertainties/U-001.png",
  "candidate_values": ["s", "5"],
  "previous_value": null,
  "current_value": "[待人工确认]",
  "reason": "blur and similar glyph shapes",
  "affects_meaning": true
}
```

Do not require candidate values when none are defensible. `status` is `unresolved` or `resolved`; retain resolved entries for traceability.

## Append-only revision history

Every confirmed change has all of these fields:

```json
{
  "uncertainty_id": "U-001",
  "previous_value": "[待人工确认]",
  "current_value": "5",
  "confirmed_by": "user",
  "confirmed_at": "2026-08-11T16:00:00+08:00",
  "note": "User confirmed the scanned character as 5."
}
```

`confirmed_by` is exactly `source-visual` or `user`. A user-provided correction must be `user`; never disguise it as a source-visual or model confirmation. The history value must match the resolved uncertainty's current value.

## Fresh-pass and final fields

For schema `1.1`, `fresh_passes` has `completeness`, `formula`, `visual-assets`, and `text`. Each records `completed`, `source_reopened`, timestamp, reviewer, checked items/counts, findings, and evidence paths. The `visual-assets` pass also has a non-empty `review_scope`, package-contained non-empty `evidence` paths, and `inventory_outcome`. With assets, `inventory_outcome` is `assets-reviewed` and `reviewed_asset_ids` covers every visual asset exactly once (duplicates fail). With none, it is `no-visual-assets`, `reviewed_asset_ids` is empty, and evidence must include `audit/visual-inventory.json`. That JSON declares `kind: visual-inventory`, `version: 1`, `status: COMPLETE`, `asset_count: 0`, and a non-empty `reviewed_source_pages` list. Manifest pages are validated first and must each have non-empty string `page_id` and `derived_page_sha256`; duplicate page IDs are invalid. The inventory list is then a strict one-to-one audit copy: exactly one object with only those two string fields for every manifest page, with no duplicate IDs/rows, missing pages, extra pages, or changed hashes. Each pass starts by reopening the original scan.

Legacy schema `1.0` keeps the former `image` key only for compatibility. It is never accepted in place of `visual-assets` for a schema `1.1` package.

`final_consistency` contains answers `1` through `10` in the same order defined in `qa-and-report.md`. Empty or inferred answers fail the delivery gate.
