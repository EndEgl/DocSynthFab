# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - fastapi>=0.110,<1.0
# - uvicorn[standard]>=0.27,<1.0
# - pypdfium2>=4,<5
# - Pillow>=10,<12

from __future__ import annotations

import base64
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional

import pypdfium2 as pdfium
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="AI1 Gen LaTeX Renderer", version="0.1.0")


TEMPLATE = r"""
\documentclass[12pt]{article}
\usepackage[margin=1pt]{geometry}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\begin{document}
\noindent
$\displaystyle %s$
\end{document}
"""


class RenderRequest(BaseModel):
    expr: str
    dpi: int = 300
    timeout_s: int = 30


class RenderResponse(BaseModel):
    ok: bool
    png_base64: Optional[str] = None
    error: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


def run_pdflatex(work: Path, timeout_s: int) -> tuple[bool, str, str]:
    proc = subprocess.run(
        [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "main.tex",
        ],
        cwd=str(work),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_s,
    )

    main_log = ""
    main_log_path = work / "main.log"
    if main_log_path.exists():
        main_log = main_log_path.read_text(encoding="utf-8", errors="replace")[-4000:]

    miktex_log = ""
    miktex_log_path = Path("/var/lib/miktex/.miktex/texmfs/data/miktex/log/pdflatex.log")
    if miktex_log_path.exists():
        miktex_log = miktex_log_path.read_text(encoding="utf-8", errors="replace")[-4000:]

    combined_stdout = (
        proc.stdout[-4000:]
        + "\n\n=== main.log tail ===\n"
        + main_log
        + "\n\n=== miktex pdflatex.log tail ===\n"
        + miktex_log
    )

    return proc.returncode == 0, combined_stdout, proc.stderr[-4000:]


def pdf_to_png_b64(pdf_path: Path, dpi: int) -> str:
    pdf = pdfium.PdfDocument(str(pdf_path))
    page = pdf[0]
    scale = dpi / 72.0
    bitmap = page.render(scale=scale)
    img = bitmap.to_pil().convert("RGBA")

    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@app.post("/render", response_model=RenderResponse)
def render(req: RenderRequest) -> RenderResponse:
    try:
        with tempfile.TemporaryDirectory(prefix="ai1_latex_", dir="/tmp") as td:
            work = Path(td)
            tex_path = work / "main.tex"
            pdf_path = work / "main.pdf"

            tex_path.write_text(TEMPLATE % req.expr, encoding="utf-8")

            ok, stdout, stderr = run_pdflatex(work, req.timeout_s)
            if not ok:
                return RenderResponse(
                    ok=False,
                    error="latex-command-failed",
                    stdout=stdout,
                    stderr=stderr,
                )

            if not pdf_path.exists():
                return RenderResponse(
                    ok=False,
                    error="latex-pdf-not-created",
                    stdout=stdout,
                    stderr=stderr,
                )

            png_b64 = pdf_to_png_b64(pdf_path, req.dpi)
            return RenderResponse(ok=True, png_base64=png_b64)

    except Exception as e:
        return RenderResponse(ok=False, error=repr(e))