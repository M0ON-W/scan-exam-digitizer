---
name: scan-exam-digitizer
description: Use when university paper exam photos, scanned pages, multipage image sets, or image-only PDFs need faithful digitization, especially when they contain Chinese or English text, mathematical or engineering notation, tables, circuits, waveforms, plots, diagrams, skew, blur, shadows, folds, handwriting, or uncertain characters.
---

# Scan Exam Digitizer

## 核心契约

- 原始扫描件是唯一事实源；忠实转录，不改写、纠错或补全。疑似原卷错误原样保留并报告“疑似原卷如此，未擅自修改”。
- 每个视觉对象保留原始裁剪、源坐标、哈希和比较证据；禁止生成式重建、臆测、补画或补像素。
- 仅在视觉确认且可确定复现时使用 `structured-text`/`vector-redraw`，否则使用 `source-crop`；不清楚的内容写 `[待人工确认]`。
- OCR、模型置信度、课程知识和答案只能定位复核区域，不能替代原图确认或改变 `VERIFIED`。

## Reference 加载规则

- 开始前读 [tool-routing.md](references/tool-routing.md)，按需读 [dependencies.md](references/dependencies.md)。
- 选择模式前读 [fidelity-and-uncertainty.md](references/fidelity-and-uncertainty.md) 和 [manifest-schema.md](references/manifest-schema.md)。
- 使用 LaTeX/TikZ/Circuitikz/PGFPlots 前读 [latex-and-layout.md](references/latex-and-layout.md)，交付前读 [qa-and-report.md](references/qa-and-report.md)。

## 流程

1. 冻结输入、页序、页边界和 SHA-256，清点视觉对象及题目归属。
2. 逐页逐题重新打开原图，先理解题目功能、图形功能、信号/表格含义，再决定重绘或裁切；不得先凭外观绘制。
3. 运行匹配的 PRE-FLIGHT；基础能力缺失为 `BLOCKED`，条件能力缺失只让受影响对象使用 `source-crop`。
4. 生成可编辑源、PDF、裁剪、manifest、比较证据和报告；布局必须通过 `scripts/layout_lint.py`。
5. 分开执行完整性、公式、视觉对象和文字 fresh-pass；每轮重新打开原扫描件并回答十项一致性问题。

## 语义与布局门禁

- Schema 1.2 的每个视觉对象必须有 `semantic_context`：`question_function`、`asset_function`、逐元素 `meaning_map`、`answer_inference_excluded: true`、`source_reopened: true`。
- 文字/导线/边框/标签间距至少 2 pt；表格内边距至少 3 pt、行高至少 14 pt、字号至少 8.5 pt；图表占正文宽度 65%–92%，且不得越界或裁切。
- `audit/layout-lint.json` 必须 PASS；碰撞、拥挤、比例失衡或裁切均阻止 `VERIFIED`。

## 停止与交付

- 缺页、遮挡、关键内容不清或未获准使用第三方服务时停止猜测，标记 `BLOCKED`/`DRAFT-UNVERIFIED`。
- 状态只能为 `BLOCKED`、`DRAFT-UNVERIFIED` 或 `VERIFIED`，且 manifest、报告、验证结果一致。未经用户批准，不安装、不发布、不覆盖现有 Skill。
