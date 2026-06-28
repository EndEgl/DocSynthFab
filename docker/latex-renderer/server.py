# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - fastapi>=0.110,<1.0
# - uvicorn[standard]>=0.27,<1.0
# - pypdfium2>=4,<5
# - Pillow>=10,<12
# - pydantic>=2,<3

from __future__ import annotations

import base64
import re
import subprocess
import tempfile
import threading

from io import BytesIO
from pathlib import Path
from typing import Optional

import pypdfium2 as pdfium
from fastapi import FastAPI
from pydantic import BaseModel, Field
from PIL import Image, ImageChops


app = FastAPI(title="DocSynthFab LaTeX Renderer", version="0.1.1")
RENDER_LOCK = threading.Lock()

TEMPLATE = r"""
\documentclass[12pt]{article}
\usepackage[paperwidth=8in,paperheight=3in,margin=2pt]{geometry}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,amsfonts,mathtools}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\begin{document}
\noindent
$\displaystyle %s$
\end{document}
"""


DANGEROUS_LATEX_PATTERNS = [
    r"\\write18\b",
    r"\\input\b",
    r"\\include\b",
    r"\\openout\b",
    r"\\read\b",
    r"\\write\b",
    r"\\catcode\b",
    r"\\csname\b",
    r"\\newread\b",
    r"\\newwrite\b",
    r"\\usepackage\b",
    r"\\documentclass\b",
    r"\\begin\s*\{\s*document\s*\}",
    r"\\end\s*\{\s*document\s*\}",
]


class RenderRequest(BaseModel):
    expr: str = Field(min_length=1, max_length=4000)
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


def sanitize_latex_expr(expr: str) -> str:
    expr = str(expr or "").strip()

    if not expr:
        raise ValueError("empty-latex-expression")

    for pattern in DANGEROUS_LATEX_PATTERNS:
        if re.search(pattern, expr, flags=re.IGNORECASE):
            raise ValueError(f"dangerous-latex-command: {pattern}")

    # Çok satırlı ifadelerde LaTeX yorum problemlerini azalt.
    expr = expr.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")

    return expr


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


def crop_near_white_border(img: Image.Image, *, threshold: int = 246, pad: int = 6) -> Image.Image:
    """
    PDFium genelde beyaz arka planlı RGBA döndürür.
    Alpha tüm sayfada dolu olduğu için alpha bbox crop yetmez.
    Bu fonksiyon beyaz olmayan piksellere göre crop alır.
    """
    rgba = img.convert("RGBA")
    rgb = rgba.convert("RGB")

    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg).convert("L")

    # threshold altı farkları sıfırla, yani çok açık beyaz/antialias arka planı yok say.
    mask = diff.point(lambda p: 255 if p > (255 - threshold) else 0)
    bbox = mask.getbbox()

    if bbox is None:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(rgba.width, x1 + pad)
    y1 = min(rgba.height, y1 + pad)

    return rgba.crop((x0, y0, x1, y1))


def white_to_alpha(img: Image.Image, *, white_threshold: int = 248) -> Image.Image:
    """
    Beyaz arka planı transparent yapar.
    Siyah/gri LaTeX glyph'leri alpha mask olarak kalır.
    """
    rgba = img.convert("RGBA")
    pixels = rgba.load()

    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]

            # Yakın beyaz alanları transparan yap.
            if r >= white_threshold and g >= white_threshold and b >= white_threshold:
                pixels[x, y] = (r, g, b, 0)
            else:
                # Metni siyaha yaklaştır; anti-alias gri tonlarını koru.
                darkness = 255 - int((int(r) + int(g) + int(b)) / 3)
                alpha = max(a, min(255, darkness + 40))
                pixels[x, y] = (0, 0, 0, alpha)

    return rgba


def pdf_to_png_b64(pdf_path: Path, dpi: int) -> str:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        page = pdf[0]
        scale = max(72, int(dpi)) / 72.0
        bitmap = page.render(scale=scale)
        img = bitmap.to_pil().convert("RGBA")
    finally:
        try:
            pdf.close()
        except Exception:
            pass

    img = crop_near_white_border(img, threshold=246, pad=8)
    img = white_to_alpha(img, white_threshold=248)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@app.post("/render", response_model=RenderResponse)
def render(req: RenderRequest) -> RenderResponse:
    with RENDER_LOCK:
        try:
            expr = sanitize_latex_expr(req.expr)

            dpi = max(72, min(int(req.dpi), 900))
            timeout_s = max(3, min(int(req.timeout_s), 120))

            with tempfile.TemporaryDirectory(prefix="docsynthfab_latex_", dir="/tmp") as td:
                work = Path(td)
                tex_path = work / "main.tex"
                pdf_path = work / "main.pdf"

                tex_path.write_text(TEMPLATE % expr, encoding="utf-8")

                ok, stdout, stderr = run_pdflatex(work, timeout_s)

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

                try:
                    pdf_size = pdf_path.stat().st_size
                except Exception as stat_exc:
                    return RenderResponse(
                        ok=False,
                        error=f"latex-pdf-stat-failed: {stat_exc!r}",
                        stdout=stdout,
                        stderr=stderr,
                    )

                if pdf_size <= 0:
                    return RenderResponse(
                        ok=False,
                        error="latex-pdf-empty",
                        stdout=stdout,
                        stderr=stderr,
                    )

                try:
                    png_b64 = pdf_to_png_b64(pdf_path, dpi)
                except Exception as pdf_exc:
                    return RenderResponse(
                        ok=False,
                        error=f"latex-pdf-to-png-failed: {pdf_exc!r}",
                        stdout=stdout,
                        stderr=stderr,
                    )

                return RenderResponse(ok=True, png_base64=png_b64)

        except subprocess.TimeoutExpired as e:
            return RenderResponse(
                ok=False,
                error="latex-timeout",
                stdout=str(getattr(e, "stdout", "") or "")[-4000:],
                stderr=str(getattr(e, "stderr", "") or "")[-4000:],
            )

        except Exception as e:
            return RenderResponse(ok=False, error=repr(e))


