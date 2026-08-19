# LaTeX and layout rules

## Engine and text

Use a Unicode-capable engine (XeLaTeX, LuaLaTeX, or compatible Tectonic) with an available Chinese font. Ordinary Chinese/English text must remain real text, never page-sized images. Keep an editable `.tex` source and all referenced original crops.

## Math transcription

- Put every mathematical, physical, and engineering expression in LaTeX. Do not substitute raw OCR, Unicode lookalikes, or formula screenshots when LaTeX can express it.
- Use `\(...\)` for inline math and `\[...\]`, `equation`, `align`, `cases`, or matrix environments for displayed structures.
- Preserve signs, relations, case, accents, superscripts/subscripts, fraction grouping, radical extent, integral/sum/limit bounds, bracket size, matrix elements, vector notation, differential symbols, complex unit, Greek identity, and units.
- Use semantic forms such as `\frac{a}{b}`, `e^{-2t}`, `X(j\omega)`, `\int_{-\infty}^{\infty}`, `\sum_{k=0}^{N}`, `\lim_{x\to0}`, `\sqrt{...}`, `\begin{cases}...\end{cases}`, and `\begin{bmatrix}...\end{bmatrix}`.
- Variables are normally italic; operators/functions use `\sin`, `\ln`, `\exp`, `\mathcal{L}`, etc.; descriptive subscripts and units use upright forms such as `V_{\mathrm{out}}` and `10\,\mathrm{k\Omega}`. Preserve the source convention when it is visibly intentional.
- Do not normalize a teacher's notation merely because another convention is preferable.

Compare mathematical structure to the scan, not just similar-looking characters. Pay special attention to `l/1`, `O/0`, `S/5`, `ν/v`, `ω/w`, `ρ/p`, `μ/u`, `λ/A`, minus signs, and exponent `t/1` confusions.

## Structure and layout

Preserve title, institution/course metadata, time, student-information fields, major-question and subquestion hierarchy, printed scores, options, fill lines, answer areas, tables, pagination order, and the positional relationship among prompt, formula, and figure. Pixel identity is unnecessary; logical identity is mandatory.

Do not float a figure away from its question. Prefer fixed or tightly controlled placement and explicit labels in source code. A page break may move content only when question ownership remains unambiguous.

## Tables and visual assets

Apply the semantic-element gate and mode record in `fidelity-and-uncertainty.md` before choosing a layout tool. Do not select a tool because it creates a prettier approximation.

- A fully confirmed table uses `structured-text`: `tabular`, `array`, or a suitable long-table structure, with real editable text and LaTeX in formula cells. Preserve meaningful spanning, rules, alignment, headers, values, and units. Long tables and multirow cells are conditional `table` capability features: PRE-FLIGHT must confirm `longtable.sty` and `multirow.sty` before using them; otherwise record the table capability as `DEGRADED` and retain a traceable `source-crop`. Keep the raw crop even though the output is text.
- A fully confirmed block/signal-flow diagram uses deterministic TikZ; a circuit uses Circuitikz with TikZ; a plot/waveform uses PGFPlots with TikZ, or direct TikZ only when the source visibly fixes every coordinate and segment. Store the editable `.tex` asset, compile it through `scripts/render_vector_asset.py`, and retain its rendered PDF/build record.
- Place a `vector-redraw` or `source-crop` adjacent to its owning prompt; never let a page break make question ownership ambiguous. A source crop is a faithful fallback, not an excuse to omit its raw-crop audit trail, element checklist, comparison evidence, and specific fallback reason.
- Do not use screenshots, a canvas export with no editable source, generative imagery, or inferred data to stand in for an editable reconstruction. If a required element is uncertain or the matching conditional dependency cannot be made available and rechecked, use `source-crop` under the fallback rule.

## Compilation and text-layer check

Compile through `scripts/compile_exam.py`, inspect warnings/errors, render all pages, and extract text. Confirm representative Chinese, English, question numbers, and ordinary table cells are present in extracted text. Formula visual fidelity is checked against the scan in the formula fresh pass; text extraction alone cannot validate mathematical meaning.
