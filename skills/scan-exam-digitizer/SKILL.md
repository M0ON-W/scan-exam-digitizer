---
name: scan-exam-digitizer
description: Use when university paper exam photos, scanned pages, multipage image sets, or image-only PDFs need faithful digitization, especially when they contain Chinese or English text, mathematical or engineering notation, tables, circuits, waveforms, plots, diagrams, skew, blur, shadows, folds, handwriting, or uncertain characters.
---

# Scan Exam Digitizer

## 核心契约

- 原始扫描件是唯一事实源。忠实转录，不改写、解释、纠错或补全；疑似原卷错误原样保留并报告“疑似原卷如此，未擅自修改。”
- 可完整复现且语义元素均经视觉确认时，优先忠实的 `structured-text` 或 `vector-redraw`；否则使用可追溯的 `source-crop`。每个视觉对象都保留原始裁剪作为审计证据，禁止生成式重建、臆测、补画或补像素。
- 无法从原图可靠确认的字符、数字、公式或图中标记写作 `[待人工确认]`，并建立 manifest、局部原图和报告项。宁缺勿猜。
- 课程知识、上下文、权威指示、OCR/模型置信度、截止时间和排版便利均不能替代原图视觉确认；OCR 只可辅助定位或起草，批量结果不得未经逐页逐题视觉核对直接入稿。
- 默认不得把试卷发送到未经用户明确许可的第三方 OCR、公式识别或云端服务；按准确内容、公式、图片、结构、可搜索性、清晰度、美观、速度的顺序解决冲突。

## Reference 加载规则

- 开始前读 [tool-routing.md](references/tool-routing.md)。清点视觉对象及 PRE-FLIGHT/依赖、允许安装和复查证据时读 [dependencies.md](references/dependencies.md)。
- 为每个表格、图或不确定项选择 `structured-text`、`vector-redraw` 或 `source-crop` 前读 [fidelity-and-uncertainty.md](references/fidelity-and-uncertainty.md)。
- 建立或更新工作记录前读 [manifest-schema.md](references/manifest-schema.md)。转录及选择 LaTeX/TikZ/Circuitikz/PGFPlots 布局工具时读 [latex-and-layout.md](references/latex-and-layout.md)。
- 进入校对、状态判定或交付阶段前读 [qa-and-report.md](references/qa-and-report.md)。只加载当前阶段所需 reference；不得凭记忆替代门禁。

## 主流程

1. 冻结输入：记录原始文件列表、顺序与 SHA-256；不覆盖源文件。
2. 执行 visual-object inventory：清点每个视觉对象（`table`、`block-diagram`、`signal-flow`、`circuit`、`plot-waveform`）、题目归属与源区域；先记录候选模式，后运行匹配的依赖 PRE-FLIGHT。
3. 实测逐页视觉读取、裁剪、文件生成、LaTeX 编译、PDF 渲染、文本提取及含中文/数学的冒烟测试。基础能力缺失即 `BLOCKED`；条件能力缺失仅让对应对象 `source-crop`。获准安装后记录包名/版本，重新运行检查并保存结果。
4. 逐页检查页数、顺序、旋转、倾斜、模糊和裁边，记录页面几何、工作 DPI 与派生页 SHA-256；再逐页逐题转录文字、公式、表格、图和不确定项。
5. 对每个视觉对象执行语义元素完整性门禁；合格者以确定性可编辑源重建，否则保留源裁剪和明确原因。所有模式均保存原始裁剪、哈希、清单及比较证据。
6. 生成可编辑源和初稿 PDF，验证真实文本层；生成逐页和视觉对象对照材料。
7. 执行分离的 fresh-pass：完整性、公式、视觉对象、文字；每轮重新打开原扫描件。回答十项一致性问题，运行交付验证并输出报告。

## 停止条件

- 基础 PRE-FLIGHT 能力缺失、疑似缺页/页序无法确定、关键区域裁掉或遮挡：保留现状，`BLOCKED` 或请求人工确认，不猜测。
- 不可靠内容保留 `[待人工确认]`；若改变题意，禁止 `VERIFIED`。未获许可的第三方服务或要求生成、推断原图细节时停止该动作。
- 所有给定选项均违反契约时，拒绝假三选一，执行最接近的合规替代。

## 交付门禁

- 非 `BLOCKED` 交付 PDF、可编辑源、manifest、报告、fresh-pass/对照证据，以及每个视觉对象的原始裁剪和模式证据；`BLOCKED` 只交付冻结源记录、PRE-FLIGHT 证据和阻断报告。
- 状态只能是 `BLOCKED`、`DRAFT-UNVERIFIED` 或 `VERIFIED`，且 manifest、报告和验证结果一致。未完成 PRE-FLIGHT、四轮 fresh-pass、文本层/视觉对象检查、十项回答或存在改变题意的未决项时，禁止 `VERIFIED`。
- 未经用户明确批准，不安装、不发布、不覆盖现有 Skill。
