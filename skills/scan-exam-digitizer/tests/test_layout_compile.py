from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from helpers import portable_tectonic, run_script


LAYOUT_TEX = r"""
\documentclass[11pt,a4paper]{article}
\usepackage[margin=18mm]{geometry}
\usepackage{fontspec,xeCJK,amsmath,array,booktabs,circuitikz}
\IfFontExistsTF{Noto Serif CJK SC}{\setCJKmainfont{Noto Serif CJK SC}}{\setCJKmainfont{AR PL UMing CN}}
\setmainfont{Times New Roman}
\IfFontExistsTF{Noto Serif CJK SC}{\newfontfamily\zhfont{Noto Serif CJK SC}}{\newfontfamily\zhfont{AR PL UMing CN}}
\input{layout-helpers.tex}
\begin{document}
{\zhfont\bfseries 题目功能：根据控制信号判断电路输出。}

\begin{center}
  \begin{circuitikz}[x=1cm,y=1cm]
    \ScanFigureSlot{
    \ScanWire{(0,1)--(1,1)}
    \draw (1,1) to[R,l=$R_1$] (3,1);
    \ScanWire{(3,1)--(4,1)}
    \ScanLabel[at={(0,1.35)}]{CLK}
    \ScanLabel[at={(3.85,1.35)}]{Q}
    }
  \end{circuitikz}
\end{center}

{\zhfont\bfseries 表格功能：列出题目中可见符号及其含义。}
\begin{center}
\ScanTableCell{
  \begin{tabular}{@{}ll@{}}
    \toprule
    {\zhfont 符号} & {\zhfont 含义} \\
    \midrule
    $CLK$ & {\zhfont 时钟输入} \\
    $Q$ & {\zhfont 输出端} \\
    \bottomrule
  \end{tabular}}
\end{center}
\end{document}
"""


class LayoutCompileTests(unittest.TestCase):
    def test_circuit_and_table_compile_render_and_extract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "exam.tex"
            source.write_text(LAYOUT_TEX, encoding="utf-8")
            shutil.copy2(
                Path(__file__).resolve().parents[1] / "assets" / "layout-helpers.tex",
                root / "layout-helpers.tex",
            )
            result = run_script(
                "compile_exam.py",
                "--source",
                source,
                "--output-dir",
                root / "out",
                "--engine",
                portable_tectonic(),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("Overfull \\hbox", result.stdout + result.stderr)
            pdf = root / "out" / "exam.pdf"
            self.assertTrue(pdf.is_file())
            extracted = "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf)).pages)
            for anchor in ("CLK", "Q", "R1", "符号", "含义"):
                self.assertIn(anchor, extracted)

            rendered_dir = root / "rendered"
            rendered_dir.mkdir()
            render = subprocess.run(
                [
                    "pdftoppm",
                    "-png",
                    "-r",
                    "180",
                    str(pdf),
                    str(rendered_dir / "page"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            pages = sorted(rendered_dir.glob("page-*.png"))
            self.assertEqual(len(pages), 1)
            with Image.open(pages[0]) as page:
                grayscale = page.convert("L")
                pixels = grayscale.get_flattened_data() if hasattr(grayscale, "get_flattened_data") else grayscale.getdata()
                dark_pixels = sum(1 for pixel in pixels if pixel < 80)
            self.assertGreater(dark_pixels, 1000)


if __name__ == "__main__":
    unittest.main()
