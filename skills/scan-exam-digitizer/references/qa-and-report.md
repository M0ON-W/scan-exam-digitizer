# Fresh-pass QA and reporting

## Four separated fresh passes

These are four separate reviews, not one continuous review relabeled four times. At the start of each pass, close derived assumptions, reopen the original scan, and record `source_reopened: true`. The original scan is the sole fact source; do not judge correctness only from OCR, LaTeX, the draft PDF, prior notes, or another pass.

1. **Completeness fresh pass** — compare page by page; verify pages, question hierarchy, scores, options, formulas, figures, tables, instructions, and no accidental merge/split. Produce a full question checklist.
2. **Formula fresh pass** — compare each formula's mathematical structure: signs, relations, powers, indices, numerators/denominators, bounds, radical/bracket extent, complex unit, differentials, Greek letters, vectors, matrix elements, and units.
3. **Visual-asset fresh pass** — compare every reconstructed and source-cropped asset against its reopened source region; together these reconstructed and source-cropped assets form the visual-asset review set. Confirm the correct source page/question, source bbox, raw-crop audit evidence (path and hash), selected mode and decision/fallback reason, and orientation. For `vector-redraw`, compare every applicable checklist element (nodes/components, connections/directions, labels, values, units, axes/ticks, curves, arrows, grouping) and verify reconstruction source, rendered asset, build record, toolchain, and comparison evidence. For `structured-text`, compare all table cells/spans/formulas and real-text linkage. For `source-crop`, confirm that the delivered crop is faithful and its fallback reason is specific. Reject generative alterations, invented elements, missing raw crops, or a comparison that merely checks appearance instead of semantic elements.
4. **Text fresh pass** — compare terminology, wording, numeric values, units, Latin case, punctuation, question numbers, and scores; explicitly review similar glyph pairs.

Any change discovered in a pass is corrected, logged, and rechecked against the original. A correction does not allow skipping the remaining passes.

## Visual-asset acceptance evidence

Before a visual object can have `qa_status: PASS`, its manifest/report must contain the following evidence. This is in addition to the page-level comparison sheets.

| Mode | Required evidence |
| --- | --- |
| All modes | asset/question/source-page IDs, source bbox, immutable raw crop and SHA-256, typed element checklist, decision reason, and visual source/output comparison evidence |
| `vector-redraw` | editable reconstruction source, rendered output and SHA-256, deterministic build record/toolchain, and fresh comparison of every checklist element |
| `structured-text` | table ID and editable text/formula block IDs, plus fresh comparison of each meaningful cell/span |
| `source-crop` | the delivered source crop, matching hash, and structured `fallback_reason`: controlled code, affected elements, one raw-source anchored observation per element, and raw-crop/comparison evidence reference; unavailable capability instead links canonical `audit/preflight.json` with its degradable failed capability, missing-requirement probes, and `source-crop` routing |

An uncertain meaning-bearing visual element requires an uncertainty record and prevents `VERIFIED`; retaining its `source-crop` preserves evidence but does not resolve it. The QA reviewer must use a fresh source inspection, not OCR confidence or a prior reconstruction decision.

## Final consistency answers

Answer all ten before delivery:

1. How many pages are in the original?
2. How many pages are in the output?
3. How many major questions were identified?
4. How many subquestions were identified?
5. Are any uncertainty items present?
6. Does every visual asset retain raw-crop audit evidence and its selected-mode evidence?
7. Are any formulas not reliably identified?
8. Is any page suspected missing?
9. Are question numbers continuous or faithful to the source?
10. Is every source visual asset linked to the correct question and compared in its selected mode?

## Check-report template

```markdown
# 检查报告

## 文档信息
- 原始文件：
- 原始页数：
- 输出页数：
- 识别大题数：
- 识别小题数：
- 状态：BLOCKED / DRAFT-UNVERIFIED / VERIFIED

## 完整性
- 缺页：无 / 有（说明）
- 漏题：无 / 有（说明）
- 漏图：无 / 有（说明）
- 页序异常：无 / 有（说明）
- 题号清单：

## 公式检查
- 公式总数：
- 已核对：
- 待确认：

## 视觉对象检查
- 视觉对象总数：
- `structured-text` / `vector-redraw` / `source-crop`：
- 已核对 / 待确认：
- 原始裁剪与哈希：
- fallback 原因：

## Fresh-pass 证据
- 完整性：原扫描件已重新打开 / 证据路径
- 公式：原扫描件已重新打开 / 证据路径
- 视觉对象：原扫描件已重新打开 / 证据路径
- 文字：原扫描件已重新打开 / 证据路径

## 人工确认项目
无

<!-- 如存在则逐项：页码、题号、位置、问题、原图局部、当前判断、置信程度（仅定位辅助）、uncertainty_id -->

## 最终一致性
1. ...
2. ...
3. ...
4. ...
5. ...
6. ...
7. ...
8. ...
9. ...
10. ...

## 声明
VERIFIED 表示规定的源文件对照检查均已执行并通过，不构成绝对零错误保证。
```

## Status gate

- `BLOCKED`: required capability or source material is missing; stop bulk work. Its minimal package contains frozen source records, manifest, the blocking report, and canonical `audit/preflight.json` evidence (`kind`, schema `1.0`, `BLOCKED` status, and a failed capability or dependency requirement with a non-empty reason). It may omit final PDF/source/figure artifacts and fresh passes rather than fabricate them to satisfy a delivery checklist.
- `DRAFT-UNVERIFIED`: useful draft exists but one or more required checks or meaning-affecting confirmations remain.
- `VERIFIED`: every required source comparison passed, no meaning-affecting unresolved item remains, text layer and artifacts validate. It is not an absolute zero-error guarantee.

Manifest, report, and `audit/validation.json` must agree. Never claim “all correct” when uncertainty remains.
