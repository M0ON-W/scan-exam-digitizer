---
name: scan-exam-digitizer
description: Split scanned university exam PDFs by year, convert every question into editable LaTeX, redraw reliable technical figures or retain source crops, and compile and visually inspect readable year-specific PDFs. Do not use for exam-topic analysis or solving questions.
---

# Scan Exam Digitizer

## Required result

Produce a separate digital package for each identified year. Each package contains editable LaTeX source, a compiled PDF, and only the original image crops that were needed because reliable redraw was not possible.

## Runtime and helpers

Required runtime:

- Python 3.10 or newer.
- `pypdf>=5`, `PyMuPDF>=1.24`, and `Pillow>=10`, installable with `python -m pip install -r requirements.txt`.
- XeLaTeX, LuaLaTeX, or Tectonic.
- For the supplied template: `ctex`, `amsmath`, `amssymb`, `mathtools`, `graphicx`, `booktabs`, `array`, `enumitem`, TikZ, Circuitikz, and PGFPlots.

Use the helpers only for their direct jobs:

```text
python scripts/render_pdf_pages.py source.pdf rendered-source
python scripts/split_pdf_by_year.py source.pdf papers --paper 2024=1-4 --paper 2023=5-8
python scripts/crop_source_image.py rendered-source/page-001.png crops/q1.png --bbox 100 200 900 700
python scripts/compile_latex.py 2024/exam.tex 2024/build --engine xelatex
```

`compile_latex.py` compiles the source and renders every output page into `rendered-pages`; the agent must then inspect those images as required below. Start from `assets/exam-template.tex` when no project template is supplied.



## 1. Divide the scan by year

- Inspect covers, headers, dates, question numbering, page sequence, and exam/answer boundaries before transcription.
- Group pages into separate year-specific papers and record the original PDF page range for each paper.
- Do not guess an uncertain year or boundary. Mark it `[待人工确认]` and keep the affected pages together until the boundary can be resolved.

## 2. Understand each question before digitizing it

Read the complete question first: stem, subquestions, options, formulas, tables, diagrams, labels, and the relationship among them. Determine what the question asks and what role each element plays before choosing a transcription or figure method.

Use the whole-question meaning, visible character traces, neighboring notation, options, and figure relationships to resolve a blurred detail when they support one reliable reading. If more than one materially different reading remains plausible, write `[待人工确认]` and retain a contextual crop. Do not use an answer key to insert content that is not supported by the scanned question.

## 3. Create editable LaTeX

- Convert question text, numbering, printed scores, options, formulas, matrices, cases, and reliably readable tables into editable LaTeX rather than screenshots or OCR-only text.
- Preserve the original hierarchy and notation, including signs, superscripts, subscripts, fractions, bounds, Greek letters, units, and option labels.
- Keep figures next to the question they belong to and keep each year's source in a separate folder or document.

## 4. Decide whether to redraw each image

For every table, circuit, block diagram, signal-flow graph, waveform, or plot:

1. Identify its function in the question and inspect all meaning-bearing elements, including components or nodes, connections, arrows, labels, values, units, axes, scales, and curves.
2. If those elements are reliably readable, redraw the object with an editable method suited to it, such as LaTeX tables, TikZ, Circuitikz, or PGFPlots.
3. If an exact redraw would require guessing a meaning-bearing element, crop and retain the original image instead. Add `[待人工确认]` beside any unresolved text that affects the question.

Redraws must preserve the source meaning; understanding the question guides disambiguation and layout, not invention.

## 5. Make the result readable

Use consistent typography and spacing. Keep labels clear of wires, symbols, borders, and other text; avoid clipping, crowding, tiny figures, oversized figures, and awkward page breaks. Tables and figures should be easy to read and visually balanced with the surrounding question. Adjust the layout to the actual content rather than enforcing universal numeric thresholds.

## 6. Compile and inspect the PDF

Compile each year's LaTeX source, then render every resulting PDF page to an image and inspect the rendered pages. Check that:

- Chinese and English text display correctly;
- formulas, matrices, symbols, subscripts, superscripts, and units are intact;
- options, tables, images, circuits, plots, and captions are complete;
- figures have readable sizes and no text-line collisions or clipping;
- page breaks, whitespace, and information density make the paper comfortable to read.

Fix observed rendering or layout problems and render the affected pages again. A successful compile alone is not sufficient.

## Stopping point

Deliver the year-separated `.tex` and `.pdf` files, the source page ranges, the retained crops, and a concise list of unresolved items. Do not create unrelated analysis, answers, or extra process artifacts. Stop when every requested year has been compiled and its rendered pages have been visually checked.
