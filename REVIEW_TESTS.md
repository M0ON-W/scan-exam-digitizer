# Review tests

Run from the plugin root. These tests are review instructions; they do not authorize public publication. Do not install dependencies solely to run them.

## Behavior-routing review matrix

The following prompts are the fixed routing cases for the digitizer. They must be checked against the packaged `SKILL.md` boundaries and recorded as pass/fail during release review.

### Positive cases

1. Image-only PDF → freeze the input, run dependency preflight, and preserve page-level source evidence.
2. Multi-page exam photos → preserve input order, page identifiers, and source hashes before transcription.
3. Exam containing a circuit diagram → retain a source crop or a fully visually verified structured/vector representation; do not invent labels.
4. Exam containing a waveform or coordinate plot → preserve axes, labels, curves, and source linkage, falling back to a source crop when uncertain.
5. Blurry or occluded material requiring an uncertainty register → record `[待人工确认]`, uncertainty evidence, and a controlled non-`VERIFIED` result.

### Negative cases

1. Reliable text exam asking for statistical analysis → route to `$exam-paper-analyzer`.
2. Request to generatively redraw the original figure → reject generative reconstruction and preserve the source crop instead.
3. Key pages are missing but the user asks for a guess → return controlled `BLOCKED`; do not infer the missing content.

## Submission test-case details

The following cases are the reviewer-facing cases for the OpenAI submission form. Use sanitized or synthetic fixtures only; do not upload private exam papers, student data, credentials, or real course records. Each case names the expected workflow, minimum result shape, and a safe fallback when the fixture is unavailable.

### Positive submission cases

1. **Image-only PDF**
   - **User prompt:** “使用 `scan-exam-digitizer` 处理这份 image-only PDF；先冻结输入文件列表和 SHA-256，再做依赖预检和页面清点，不要猜测内容。”
   - **Expected behavior:** Freeze the input manifest and hashes, run the documented dependency preflight, preserve page order, and inventory pages/visual objects before transcription.
   - **Expected result shape:** An input manifest with file hashes, dependency/preflight status, page inventory, visual-object inventory, and an explicit `VERIFIED`, `DRAFT-UNVERIFIED`, or `BLOCKED` state.
   - **Fixture / fallback:** A synthetic image-only PDF with no student or exam-identifying data. If required base capability is missing, return the documented `BLOCKED` result rather than claiming a complete delivery.

2. **Multi-page exam photos**
   - **User prompt:** “按原始顺序处理这组多页试卷照片，先记录页标识和 SHA-256，再逐页建立转录和来源关联。”
   - **Expected behavior:** Preserve the original file order and page identifiers, freeze hashes, and maintain page-level source links throughout the workflow.
   - **Expected result shape:** A manifest containing ordered input files, page IDs, hashes, page-level processing records, and unresolved-item status.
   - **Fixture / fallback:** A synthetic set of three or more page images with no private content. If ordering or page completeness cannot be established, stop with `BLOCKED` or a review-needed result.

3. **Circuit diagram**
   - **User prompt:** “处理这页含电路图的试卷；只在视觉上完全确认时结构化或矢量化，否则保留可追溯的 source-crop，不要补画标签。”
   - **Expected behavior:** Inspect the original diagram, preserve a source crop unless every semantic element is visually confirmed, and never generatively redraw or invent labels.
   - **Expected result shape:** A visual-object record with page/region locator, source-crop path or verified representation, reconstruction provenance, uncertainty fields, and final status.
   - **Fixture / fallback:** A synthetic circuit image with at least one labeled component. If any label or connection is ambiguous, retain the crop and mark the uncertainty instead of reconstructing it.

4. **Waveform or coordinate plot**
   - **User prompt:** “处理这张含波形和坐标轴的图；保留坐标轴、刻度、标签、曲线和原图关联，无法确认时使用 source-crop。”
   - **Expected behavior:** Preserve axes, labels, curves, and the source linkage; use structured/vector output only for visually verified elements.
   - **Expected result shape:** A plot record with page/region locator, visual elements, source-crop or verified vector asset, provenance, and uncertainty/fresh-pass status.
   - **Fixture / fallback:** A synthetic coordinate plot. If a scale, label, or curve cannot be reliably read, keep the original crop and report the unresolved field.

5. **Blurry or occluded material**
   - **User prompt:** “处理这张有模糊和遮挡的试卷，登记所有不确定字符和公式；不得把推测内容标为 `VERIFIED`。”
   - **Expected behavior:** Record `[待人工确认]` items and evidence, preserve source crops, and keep the output in a controlled non-`VERIFIED` state until the ambiguity is resolved.
   - **Expected result shape:** An uncertainty register with page/region references, affected text or visual object, source evidence, resolution state, and an explicit `DRAFT-UNVERIFIED` or `BLOCKED` result.
   - **Fixture / fallback:** A synthetic blurred/occluded image. If the ambiguity changes meaning and cannot be resolved, return the uncertainty register and stop rather than guessing.

### Negative submission cases

1. **Reliable text exam asking for statistical analysis**
   - **User prompt:** “这是一份可靠文字层的结构化试卷，请统计多年题型频率和分值趋势。”
   - **Expected behavior:** Route to `$exam-paper-analyzer`; do not invoke scan digitization when no scan-fidelity task is requested.
   - **Expected result shape:** A safe routing message naming the analyzer and no digitization output.
   - **Fixture / fallback:** A synthetic text-based question bank. If the user actually supplies an image-only source, request the scan and return to the digitizer workflow.

2. **Generative redraw request**
   - **User prompt:** “请根据这张模糊电路图生成一张看起来完整的新图，缺少的标签请你补上。”
   - **Expected behavior:** Refuse generative reconstruction and preserve the original source crop; do not infer missing pixels, labels, or connections.
   - **Expected result shape:** A refusal/safe-fallback explanation plus the required source-crop and uncertainty handling, without an invented figure.
   - **Fixture / fallback:** A synthetic ambiguous circuit image. The safe fallback is the source crop with unresolved labels recorded.

3. **Missing key pages with a request to guess**
   - **User prompt:** “第 3 页和第 4 页缺失，请根据上下文猜出题目和公式并完成整份试卷。”
   - **Expected behavior:** Return controlled `BLOCKED`; do not infer missing page content from context or course knowledge.
   - **Expected result shape:** A blocked report listing missing page identifiers, the effect on completeness, and the exact evidence needed to resume.
   - **Fixture / fallback:** A synthetic two-page set with an intentionally missing middle page. The safe fallback is the blocked report and a request for the missing pages.

## Positive tests

1. **Manifest contract** — Run `python3 /mnt/c/Users/WangYue/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .` and record its output. The bundled validator is currently stale for public skill metadata: it rejects `policy.products`, while the current submission schema requires that field. Treat that exact `policy.products` error as `LOCAL_VALIDATOR_SCHEMA_MISMATCH`; any other failure is a package failure. The independent current-policy check below must pass.
2. **Baseline archive traceability** — Recompute the input archive SHA-256 and compare it with `PROVENANCE.md`; preserve the archive as the immutable baseline. The 1.1.0 tree is intentionally not byte-identical to that baseline because the semantic/layout gates, linter, layout helpers, and regression tests are documented additions.
3. **Skill metadata** — Parse `skills/scan-exam-digitizer/SKILL.md` frontmatter and `skills/scan-exam-digitizer/agents/openai.yaml` as YAML. Expected: both parse as mappings with the required skill/agent display fields.
4. **Current policy metadata** — Parse `skills/scan-exam-digitizer/agents/openai.yaml` and assert that `policy` contains only `products` and `allow_implicit_invocation`, that products are `CHAT` and `CODEX`, and that implicit invocation is boolean. Expected: all assertions pass.
5. **Python syntax** — Run `python3 -m compileall -q skills/scan-exam-digitizer/scripts`. Expected: exit code 0; no syntax errors. Remove only newly generated `__pycache__` directories after review if a clean tree is required.
6. **Skills-only boundary and listing assets** — Parse `.codex-plugin/plugin.json` and assert that `name`, `version`, `license`, and `skills` are present, `apps` and `mcpServers` are absent, and `interface.logo` plus `interface.composerIcon` resolve to regular package files. Expected: all assertions pass and every referenced skill and listing asset path exists.
7. **Semantic and layout contract** — Run `python3 -m unittest discover -s skills/scan-exam-digitizer/tests -p 'test_*.py'`. Expected: 25 tests pass, including schema `1.2`, semantic context, label/wire collision rejection, real circuit/table LaTeX compilation, PDF rendering, and text extraction.
8. **Six-copy synchronization** — Compare the relative file list and SHA-256 values of the canonical `.codex`, `.agents`, `.gemini`, wrapper, GitHub publication, and release-candidate skill trees. Expected: all six trees contain the same files and bytes; archives and historical staging snapshots remain outside the comparison scope.

## Negative tests

1. **Reject Apps declaration** — In a temporary copy only, add an `apps` field to `.codex-plugin/plugin.json` without adding `.app.json`, then run the official validator. Expected: non-zero exit with an unsupported or invalid Apps-related manifest error. Do not edit this candidate.
2. **Reject incomplete skill tree** — In a temporary copy only, remove `skills/scan-exam-digitizer/SKILL.md`, then run the official validator. Expected: non-zero exit reporting the missing `SKILL.md`. Do not edit this candidate.
3. **Reject unsafe archive path** — In a temporary test ZIP only, add a member such as `scan-exam-digitizer/../outside.txt` and run the release path-safety checker. Expected: the checker rejects the member before extraction; no file is written outside `skills/scan-exam-digitizer/`.

Record command output and the candidate commit or file manifest used for review. A passing local review does not establish public publication or account authorization.
