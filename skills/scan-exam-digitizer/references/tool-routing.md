# Tool routing and PRE-FLIGHT

## Privacy gate

Do not send any exam page, crop, OCR text, formula, metadata, or hash to an unapproved third-party OCR, formula-recognition, or cloud service. Current-environment visual and file capabilities are allowed. Package/font downloads that contain no exam content are not exam-data uploads; record them when relevant.

## Visual-object inventory and conditional dependencies

After freezing and hashing the inputs, inventory each visual object before choosing a reconstruction path: `table`, `block-diagram`, `signal-flow`, `circuit`, or `plot-waveform`. Pass every observed type to `preflight.py` with a repeatable `--asset-type` argument so it can evaluate the matching conditional capability groups.

When a conditional package is missing, the agent may install it if permitted. Rerun the dependency checker after installation and record the package name, installed version, and checker evidence in the job record. If installation remains unavailable, continue bulk digitization but route only the affected asset types to provenance-preserving source crops. A missing base dependency remains `BLOCKED`.

## Required capability check

Freeze and hash inputs first, then run `scripts/preflight.py` before transcription. Treat every row as blocking:

| Capability | Evidence required |
|---|---|
| Per-page visual reading | A page can be opened at sufficient resolution; operator records the capability, not an OCR claim |
| Image crop | A lossless crop can be created and reopened |
| File generation | The job directory and audit files can be written |
| LaTeX compile | The actual selected engine compiles the smoke source |
| PDF render | The compiled PDF renders to page images |
| PDF text extraction | Extractor recovers the Chinese and English smoke anchors |
| Math glyphs | A human/visual-model inspection of the rendered smoke page finds no obvious missing-glyph boxes |

`--visual-read-confirmed` and `--math-glyphs-confirmed` are attestations that the corresponding visual checks were actually performed. Never pass them speculatively.

## Mandatory LaTeX smoke

The smoke source must contain Chinese body text, English body text, a fraction, superscript, subscript, an integral from `-\infty` to `\infty`, Greek letters, and a matrix. PRE-FLIGHT passes only when:

1. LaTeX compilation succeeds.
2. The PDF renders successfully.
3. Chinese and English body anchors are extracted from the PDF.
4. The rendered page has no obvious missing mathematical glyphs or square boxes.

Use XeLaTeX, LuaLaTeX, or a compatible Unicode TeX engine such as Tectonic. Never silently fall back to an image-only PDF or hidden OCR layer.

## Script routing

- `preflight.py`: capability evidence and mandatory smoke test.
- `inspect_exam.py`: source hashing, PDF rasterization/image normalization, page geometry and duplicate candidates.
- `extract_source_region.py`: provenance-preserving original/processed crops.
- `compile_exam.py`: reproducible LaTeX compilation record.
- `make_comparisons.py`: full-page source/output comparison sheets.
- `validate_deliverables.py`: structural, provenance, text-layer and status gate.

The scripts are deterministic guardrails, not autonomous transcription. Visual reading, semantic formula comparison, page-order judgment, and the four fresh passes must still be performed against the original scans.
