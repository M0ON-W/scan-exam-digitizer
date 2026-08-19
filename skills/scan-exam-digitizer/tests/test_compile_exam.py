from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

from helpers import portable_tectonic, run_script


SMOKE_TEX = r"""
\documentclass{article}
\usepackage{fontspec}
\usepackage{amsmath}
\setmainfont{Times New Roman}
\IfFontExistsTF{Noto Serif CJK SC}{\newfontfamily\zhfont{Noto Serif CJK SC}}{\newfontfamily\zhfont{Microsoft YaHei}}
\begin{document}
{\zhfont 中文正文可搜索。} English searchable text.
\[
\frac{x_1^2}{y_2}+\int_{-\infty}^{\infty}e^{-\alpha t}\,dt
+\omega_0+\begin{bmatrix}1&2\\3&4\end{bmatrix}
\]
\end{document}
"""


class CompileExamTests(unittest.TestCase):
    def test_compiles_real_latex_and_preserves_text_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "exam.tex"
            source.write_text(SMOKE_TEX, encoding="utf-8")
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
            metadata = json.loads((root / "out" / "compile-result.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["status"], "PASS")
            pdf = root / "out" / "exam.pdf"
            self.assertTrue(pdf.exists())
            extracted = "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf)).pages)
            self.assertIn("中文正文可搜索", extracted)
            self.assertIn("English searchable text", extracted)


if __name__ == "__main__":
    unittest.main()
