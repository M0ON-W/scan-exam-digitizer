# Scan Exam Digitizer

用于将扫描大学试卷按年份拆分并制作成可编辑、可阅读的数字版：

1. 根据封面、年份、题号和页序划分不同年份的试卷；
2. 先理解每道题的题干、选项、公式、表格和图片，再转写为可编辑 LaTeX；
3. 对可靠可辨的表格、电路、框图、波形和曲线进行可编辑重绘，无法可靠重绘时保留原图裁剪；
4. 编译每年的 PDF，并逐页渲染检查文字、公式、图片、表格、电路图、尺寸、排版和信息密度。

最终交付按年份分开的 `.tex`、`.pdf`、必要的原图裁剪、来源页码范围和待确认项。

## 运行环境

- Python 3.10+
- `pypdf>=5`、`PyMuPDF>=1.24`、`Pillow>=10`
- XeLaTeX、LuaLaTeX 或 Tectonic
- 中文与数学排版包，以及按题图需要使用的 TikZ、Circuitikz、PGFPlots

安装 Python 依赖：`python -m pip install -r skills/scan-exam-digitizer/requirements.txt`

技能提供四个小工具：按年份拆分 PDF、渲染 PDF 页面、裁切原图区域、编译 LaTeX 并渲染全部输出页面。它们不替代 agent 对题意、模糊内容、重绘可靠性和最终版面的判断。
