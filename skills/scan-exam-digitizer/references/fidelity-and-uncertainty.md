# Fidelity, uncertainty, images, tables, and handwriting

## Sole-source rule

The original scan is the only authority for exam content. Do not select a reading because it fits course knowledge, an answer, nearby wording, conventional notation, a coordinator's assertion, or a deadline. Preserve suspected source errors and report: `疑似原卷如此，未擅自修改。`

任何模型、OCR 或识别系统给出的数值置信度只能作为定位复核区域的辅助信息，不得作为确认字符、公式或 VERIFIED 状态的依据。

## Uncertainty contract

When any content cannot be visually confirmed:

1. Put the exact marker `[待人工确认]` at the corresponding output position; do not invent alternative markers.
2. Create a stable `uncertainty_id` and a manifest entry with page, question, location, pixel bbox, candidate readings if any, reason, source crop, and status.
3. Save a local crop that includes enough surrounding context for review.
4. Repeat the item in the check report.
5. Keep the value unresolved until the source image or the user explicitly confirms it.

Never hide uncertainty only in prose. A possible reading is not a confirmed reading.

## Confirmation and revision provenance

- `confirmed_by: source-visual` means a fresh inspection of the original scan itself resolves the value.
- `confirmed_by: user` means the user supplied or selected the confirmed value. Never relabel user confirmation as model/source confirmation.
- User confirmation must be a direct, explicit value from the user for an identified uncertainty (for example, “U-017 is 5”). A prompt's report that a teacher, coordinator, manager, answer key, or other third party prefers a value is not user confirmation and remains unconfirmed against the source.
- Append a revision record containing `uncertainty_id`, `previous_value`, `current_value`, `confirmed_by`, `confirmed_at`, and `note`. Do not delete or rewrite prior history.
- Model inference, OCR agreement, confidence score, or mathematical plausibility is never a valid confirmation source.
- OCR may locate or draft a review target, but batch OCR output must not enter the transcription without the required page-by-page and question-by-question visual comparison.

## Visual reconstruction decision gate

Inventory every table and technical figure before choosing a mode. The original scan remains the factual authority: deterministic editable reconstruction is a faithful encoding of visually confirmed elements, never an interpretation of the question. `generative reconstruction is prohibited`, including generative redraw, inpainting, invented labels, inferred curves, guessed hidden pixels, or AI-created decorative detail.

For every visual object, use this ordered decision:

1. Capture an immutable **raw crop** from the source page before cleanup; retain its source bbox and SHA-256 for every mode.
2. Inspect all applicable semantic elements at usable resolution. If all are visually confirmable and the required conditional tool capability passes, choose `structured-text` for an eligible table or `vector-redraw` for an eligible diagram.
3. If any meaning-bearing element is not visually confirmable, record `[待人工确认]` where the output has text, create an uncertainty item and review crop, and do not reconstruct the unknown element. Use `source-crop` for the visual unless the entire unresolved item is excluded by the source scope.
4. If a conditional capability is unavailable after any permitted installation/recheck, take the **conditional fallback** to `source-crop` only for the affected asset. A missing base capability is `BLOCKED`.

`vector-redraw` means stored, editable text source rendered by a named deterministic toolchain. The same source, toolchain, and inputs must reproduce the asset; manual raster tracing, freehand touch-up, and output-only diagrams do not qualify. Crop-only processing may use crop, small rotation, deterministic perspective correction, background cleanup, and conservative sharpening/contrast, with every operation logged; it may not add, erase, relabel, or guess elements.

### Required mode decision record

For every `structured-text`, `vector-redraw`, or `source-crop` record, retain the asset/question/page IDs, source bbox, raw-crop path and hash, decision reason, typed **element checklist**, and source/output comparison evidence. `vector-redraw` also needs reconstruction source, rendered output/hash, build record, and toolchain. `structured-text` needs its editable text/formula block linkage. `source-crop` uses a structured `fallback_reason` with a controlled code and affected-elements list. Source-detail/uncertainty reasons require one raw-source anchored observation per affected element (issue code, element ID/type, page, bbox, and raw-crop/comparison reference); unavailable-capability reasons instead link only `audit/preflight.json`, the canonical `scan-exam-digitizer-preflight` record. Its nested dependency result must prove the requested capability is degradable, failed on named missing requirements, and has retained failing probe evidence. A vague sentence or hand-written `DEGRADED` JSON is invalid. Follow the exact manifest requirements in `manifest-schema.md`.

### Semantic-element completeness gate by asset type

All listed applicable elements must be visibly confirmed, preserved in the listed checklist, and compared after rendering. “Looks similar” is insufficient.

| Asset type | Editable mode and ordered tool | Required semantic elements | Use `source-crop` when |
| --- | --- | --- | --- |
| Table | `structured-text`: LaTeX `tabular`/`array`/long-table with LaTeX formula cells | rows, columns, headers, merged-cell meaning, cell content, formulas, values, units, meaningful borders/alignment | any cell, span, rule, formula, or meaning-bearing layout is uncertain or not reproducible; one uncertain cell still gets its own uncertainty record |
| Block or signal-flow diagram | `vector-redraw`: TikZ | every node, edge, arrow direction, branch/summing point, sign, label, value, unit, grouping, and orientation | any connection/direction/label or semantic grouping is unclear, or TikZ is unavailable |
| Circuit | `vector-redraw`: Circuitikz (with TikZ) | each component and symbol, terminal/junction, wire, polarity/direction, value, label, unit, reference designator, and orientation | any component/wire/junction/value is unclear, or Circuitikz is unavailable |
| Plot or waveform | `vector-redraw`: PGFPlots with TikZ; direct TikZ only when every visible coordinate/curve segment is exactly specified by the scan | axes, origin, scale/ticks, curves/segments, points, arrows, labels, values, units, domain/range markings, and orientation | a curve, scale, point, shading, hand-drawn trace, or value would require inference, or PGFPlots/TikZ is unavailable |

For a complete table, `structured-text` is preferred over a vector snapshot. For eligible technical figures, use the listed vector tool rather than a raster substitute. The raw crop stays mandatory audit evidence even after a successful reconstruction.

## Handwriting and marks

- Student answers, grading marks, pencil traces, and other non-printed response content are excluded by default.
- Do not use generative repair or inpainting to remove them. Crop/cleanup may not invent covered pixels.
- If non-printed marks cover the printed exam, create an uncertainty item and preserve a review crop.
- Handwriting or teacher annotation that is part of the original question itself must be preserved and identified as such.

## Status impact

An unresolved item that can change wording, value, sign, bound, index, unit, question linkage, or figure meaning prevents `VERIFIED`. Minor unresolved decoration may remain only if explicitly classified and reported without affecting exam content.
