# Scan Exam Digitizer

将大学试卷照片、扫描页或 image-only PDF 忠实整理为用户指定的格式。原始扫描件始终是事实来源：不擅自纠错、补全或根据课程知识猜测；看不清的内容标记 `[待人工确认]`；无法可靠重建的电路、表格、波形和图表保留为可追溯的原始裁剪。

默认采用最小可用流程，只检查当前交付所需的页面、文字、公式和视觉对象，只生成用户需要的文件。manifest、逐对象哈希、固定 schema、依赖预检、LaTeX 工具链、固定布局阈值和多轮独立审计均为按需能力，不是日常任务的强制步骤。

## English

Faithfully digitize university exam photos, scanned pages, or image-only PDFs into the format requested by the user. The scan remains the factual authority; unreadable content is marked for review, and uncertain technical figures are preserved as traceable source crops.

The default workflow is intentionally small. Manifests, per-object hashes, fixed schemas, dependency preflight, LaTeX reconstruction, layout gates, and multi-pass audits are used only when the user or an existing project requires them.
