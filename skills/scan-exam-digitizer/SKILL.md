---
name: scan-exam-digitizer
description: Faithfully digitize university exam photos, scanned pages, or image-only PDFs containing text, formulas, tables, circuits, plots, or other technical figures. Use for transcription or source-faithful packaging; do not use for exam analysis or solving questions by default.
---

# Scan Exam Digitizer

## Outcome

Turn the supplied scans into the format the user requested while keeping the original scan as the factual authority. Preserve meaning and uncertainty; do not expand the job into a full archival system unless requested.

## Essential rules

- Transcribe what is visible. Do not silently correct, complete, rewrite, or infer missing content from course knowledge, OCR confidence, or an answer key.
- Use OCR as a draft or locator, then check consequential text and formulas against the scan. Mark unresolved content `[待人工确认]` and retain a source crop when it helps review.
- Preserve meaning-bearing diagrams, circuits, tables, waveforms, and plots as traceable source crops when an exact editable reconstruction is uncertain. Do not use generative redraws for source figures.
- Redraw a figure only when the user wants an editable version and every relevant element can be confirmed from the source. Keep the original crop alongside it when comparison matters.
- Preserve page order and identify source pages or ranges. Do not send scans to a third-party service without the user's authorization.

## Workflow

1. Inspect the requested files, page order, readability, and output format. Record hashes only when the user asks for them or they are needed to distinguish or resume sources.
2. Digitize only the requested scope. Use the simplest suitable representation: text for clear text, editable notation for clear formulas or tables, and source crops for uncertain or meaning-bearing visuals.
3. Compare the completed output with the source at the level needed for the requested deliverable. Recheck all marked uncertainties and any content whose error would change the question.
4. Deliver the requested files with a short note covering source range, unresolved items, and the verification actually performed. Then stop.

## Scope control

- Do not require a manifest, per-object hash, fixed schema, dependency preflight, LaTeX toolchain, layout thresholds, comparison package, or multiple independent QA passes unless the user requests that level of audit or an existing project already relies on it.
- Do not create editable source, PDF, crops, reports, and audit files all at once unless they are requested or necessary for source fidelity.
- A missing optional tool should degrade only the affected output. Use a faithful crop or simpler format when that still satisfies the request; block only when the requested result cannot be produced truthfully.
- Use bundled references or scripts only when they directly help with the current requested output; their presence does not make them mandatory.

## Verification labels

Use labels only when useful to the deliverable. `VERIFIED` means the requested content was checked against the source; otherwise use `DRAFT-UNVERIFIED` or clearly describe the remaining review. Never equate a structural file check with visual verification.
