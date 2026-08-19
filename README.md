## 功能 / Capabilities

### 中文

`scan-exam-digitizer` 用于忠实处理大学试卷照片、扫描页、多页图像集和 image-only PDF，尤其适用于包含以下内容的材料：

- 中英文文字；
- 数学公式；
- 表格；
- 电路图、框图和信号流图；
- 波形、曲线和其他图表；
- 阴影、折痕、倾斜、模糊、手写和不确定字符。

原始扫描件是唯一事实源。Skill 不擅自纠错、补全、重画或解释原卷内容；无法可靠确认的字符、公式、数字或图中标记必须保留为不确定项，并使用原始裁剪作为审计证据。

### English

`scan-exam-digitizer` faithfully processes university exam photos, scanned pages, multipage image sets, and image-only PDFs, especially material containing:

- Chinese or English text;
- mathematical formulas;
- tables;
- circuits, block diagrams, and signal-flow diagrams;
- waveforms, plots, and charts;
- shadows, folds, skew, blur, handwriting, and uncertain characters.

The original scan is the sole factual source. The skill does not silently correct, complete, redraw, or reinterpret the source. Unreadable characters, formulas, numbers, and diagram labels remain explicitly marked as uncertain, with original crops retained as audit evidence.

## 工作流 / Workflow

中文：

1. 冻结原始文件列表、顺序和 SHA-256；
2. 清点页面、题目和视觉对象；
3. 根据材料类型运行依赖预检；
4. 检查页数、页序、旋转、倾斜、模糊和裁边；
5. 逐页逐题处理文字、公式、表格和图；
6. 能可靠复现时才使用结构化文本或矢量重绘；
7. 无法可靠确认时保留 `source-crop`；
8. 生成可编辑源、PDF、manifest、哈希和对照报告；
9. 执行独立 fresh-pass 并明确最终状态。

English:

1. Freeze the original file list, order, and SHA-256;
2. inventory pages, questions, and visual objects;
3. run capability-specific dependency preflight;
4. check page count, order, rotation, skew, blur, and cropping;
5. process text, formulas, tables, and figures page by page;
6. use structured text or vector redraw only when faithfully reproducible;
7. retain `source-crop` whenever reliable reconstruction is not possible;
8. generate editable source, PDF, manifest, hashes, and comparison reports;
9. perform an independent fresh pass and report the final status explicitly.

## 输入与输出 / Inputs and outputs

中文输入：

- 原始试卷照片；
- 扫描页或多页图像集；
- image-only PDF；
- 含公式、表格、电路、波形、图表或手写内容的材料。

非阻断状态下可输出：

- 可编辑源；
- PDF 初稿或交付 PDF；
- manifest；
- 逐页报告和视觉对象报告；
- 每个视觉对象的原始裁剪；
- 哈希、对照材料和 fresh-pass 证据；
- `VERIFIED` 或 `DRAFT-UNVERIFIED` 状态。

English inputs:

- Original exam photos;
- scanned pages or multipage image sets;
- image-only PDFs;
- material containing formulas, tables, circuits, waveforms, plots, or handwriting.

For a non-blocked delivery, outputs may include:

- editable source;
- draft or delivery PDF;
- manifest;
- page-level and visual-object reports;
- original crops for every visual object;
- hashes, comparison materials, and fresh-pass evidence;
- an explicit `VERIFIED` or `DRAFT-UNVERIFIED` status.

## 真实性边界 / Fidelity boundary

- OCR 只能辅助定位或起草，不能未经逐页视觉核对直接入稿。
- 禁止生成式重建、臆测、补画和虚构像素。
- 不把课程知识或模型置信度当作原图证据。
- 未经用户许可，不把试卷发送到第三方 OCR、公式识别或云端服务。
- 依赖缺失、页序不明或存在改变题意的不确定内容时，必须标记为 `BLOCKED`。

OCR may assist with locating or drafting, but it cannot enter the final output without visual verification. Generative reconstruction, guessing, invented pixels, and undisclosed third-party processing are prohibited.

## 依赖预检 / Dependency preflight

```bash
python3 skills/scan-exam-digitizer/scripts/check_dependencies.py \
  --capability base \
  --output /tmp/scan-exam-digitizer-dependencies.json
