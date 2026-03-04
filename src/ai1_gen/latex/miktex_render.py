# src/ai1_gen/latex/miktex_render.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - Pillow>=10,<12
# - PyMuPDF>=1.23,<1.25 (PDF rasterize için)

from __future__ import annotations

import json
import random
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

from PIL import Image


class LatexRenderError(RuntimeError):
    pass


def render_latex_to_rgba(
    latex_expr: str,
    *,
    pdflatex_cmd: str = "pdflatex",
    timeout_s: int = 12,
    raster_dpi: int = 300,
) -> Image.Image:
    """
    pdflatex ile tek sayfalık PDF üretir, PyMuPDF ile rasterize edip RGBA döndürür.
    """
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        raise LatexRenderError("render/latex-missing: PyMuPDF (fitz) import edilemedi") from e

    # standalone yerine article kullanıyorum (daha stabil kurulumlarda çalışır)
    tex = r"""
\documentclass[12pt]{article}
\usepackage[margin=1pt]{geometry}
\usepackage{amsmath,amssymb}
\pagestyle{empty}
\begin{document}
\noindent
$%s$
\end{document}
""" % latex_expr

    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        tex_path = td_p / "eq.tex"
        tex_path.write_text(tex, encoding="utf-8")

        # pdflatex
        try:
            subprocess.run(
                [pdflatex_cmd, "-interaction=nonstopmode", "-halt-on-error", str(tex_path.name)],
                cwd=str(td_p),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout_s,
                check=True,
            )
        except FileNotFoundError as e:
            raise LatexRenderError("render/latex-missing: pdflatex bulunamadı (MiKTeX PATH?)") from e
        except subprocess.TimeoutExpired as e:
            raise LatexRenderError("render/latex-timeout") from e
        except subprocess.CalledProcessError as e:
            raise LatexRenderError("render/latex-failed") from e

        pdf_path = td_p / "eq.pdf"
        if not pdf_path.exists():
            raise LatexRenderError("render/latex-failed")

        # rasterize
        doc = fitz.open(str(pdf_path))
        page = doc.load_page(0)
        zoom = raster_dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=True)
        img = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
        doc.close()
        return img


# ----------------------------------------------------------------------
# Random math expression generator + bank exporter
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class MathSample:
    expr: str
    png_path: str
    w: int
    h: int


_GREEK = ["alpha", "beta", "gamma", "delta", "theta", "lambda", "mu", "sigma", "phi", "omega"]
_VARS  = ["x", "y", "z", "t", "n", "k", "i", "j", "a", "b", "c"]
_FUNCS = ["\\sin", "\\cos", "\\tan", "\\log", "\\ln", "\\exp"]


def _rand_int(rng: random.Random, a: int, b: int) -> int:
    return rng.randint(a, b)


def _atom(rng: random.Random) -> str:
    p = rng.random()
    if p < 0.25:
        return str(_rand_int(rng, 1, 9))
    if p < 0.55:
        return rng.choice(_VARS)
    if p < 0.75:
        return f"\\{rng.choice(_GREEK)}"
    f = rng.choice(_FUNCS)
    v = rng.choice(_VARS)
    return f"{f}({v})"


def _expr(rng: random.Random, depth: int = 0, max_depth: int = 2) -> str:
    if depth >= max_depth:
        return _atom(rng)

    p = rng.random()

    if p < 0.40:
        left = _expr(rng, depth + 1, max_depth)
        right = _expr(rng, depth + 1, max_depth)
        op = rng.choice(["+", "-", "\\cdot"])
        return f"{left} {op} {right}"

    if p < 0.60:
        num = _expr(rng, depth + 1, max_depth)
        den = _expr(rng, depth + 1, max_depth)
        return f"\\frac{{{num}}}{{{den}}}"

    if p < 0.78:
        base = _atom(rng)
        exp = rng.choice([str(_rand_int(rng, 2, 5)), rng.choice(_VARS), f"\\{rng.choice(_GREEK)}"])
        return f"{base}^{{{exp}}}"

    if p < 0.92:
        inside = _expr(rng, depth + 1, max_depth)
        if rng.random() < 0.25:
            k = rng.choice([3, 4])
            return f"\\sqrt[{k}]{{{inside}}}"
        return f"\\sqrt{{{inside}}}"

    return _atom(rng)


def _template_equation(rng: random.Random) -> str:
    templates = [
        r"\int_{0}^{1} " + _expr(rng, 0, 2) + r"\, dx",
        r"\frac{d}{dx}\left(" + _expr(rng, 0, 2) + r"\right)",
        r"\lim_{x\to 0} \frac{\sin x}{x}",
        r"\sum_{i=1}^{n} " + _expr(rng, 0, 2),
        r"\prod_{k=1}^{n}\left(1+\frac{1}{k}\right)",
        r"\mathbf{v}=\begin{bmatrix} " + " \\\\ ".join([_expr(rng, 0, 1) for _ in range(3)]) + r" \end{bmatrix}",
        r"A=\begin{bmatrix} "
        + " & ".join([_expr(rng, 0, 1) for _ in range(3)]) + r"\\"
        + " & ".join([_expr(rng, 0, 1) for _ in range(3)]) + r" \end{bmatrix}",
        r"P(A\mid B)=\frac{P(A\cap B)}{P(B)}",
        r"A=\{x\in\mathbb{R}:\; x>" + str(_rand_int(rng, 0, 3)) + r"\}",
        r"f(x)=\begin{cases} " + _expr(rng, 0, 1) + r", & x\ge 0 \\ " + _expr(rng, 0, 1) + r", & x<0 \end{cases}",
        r"\begin{aligned} "
        r"y &= " + _expr(rng, 0, 2) + r" \\ "
        r"z &= " + _expr(rng, 0, 2) + r" "
        r"\end{aligned}",
        _expr(rng, 0, 3),
    ]
    return rng.choice(templates)


def sample_latex_expr(rng: random.Random, *, level: str = "medium") -> str:
    level = (level or "medium").strip().lower()
    if level == "clean":
        return _expr(rng, 0, 2) if rng.random() < 0.6 else _template_equation(rng)
    if level == "heavy":
        return _template_equation(rng) if rng.random() < 0.35 else _expr(rng, 0, 4)
    return _template_equation(rng) if rng.random() < 0.45 else _expr(rng, 0, 3)


def generate_math_bank(
    *,
    out_dir: str | Path,
    count: int,
    seed: int = 1337,
    pdflatex_cmd: str = "pdflatex",
    timeout_s: int = 12,
    raster_dpi: int = 300,
    unique: bool = True,
    max_tries: int = 50_000,
) -> List[MathSample]:
    """
    Belirli miktarda matematik PNG üretir.
    - out_dir içine: eq_000001.png ... + math_bank.json
    """
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    seen: Set[str] = set()
    samples: List[MathSample] = []

    tries = 0
    while len(samples) < count:
        tries += 1
        if tries > max_tries:
            break

        level = rng.choice(["clean", "medium", "heavy"])
        expr = sample_latex_expr(rng, level=level)

        if unique and expr in seen:
            continue
        seen.add(expr)

        img = render_latex_to_rgba(
            expr,
            pdflatex_cmd=pdflatex_cmd,
            timeout_s=timeout_s,
            raster_dpi=raster_dpi,
        )

        idx = len(samples) + 1
        name = f"eq_{idx:06d}.png"
        path = outp / name
        img.save(path, format="PNG", optimize=False)

        samples.append(MathSample(expr=expr, png_path=str(path), w=img.width, h=img.height))

    meta = {
        "version": "ai1-ds-v1.3.2",
        "seed": seed,
        "count": len(samples),
        "pdflatex_cmd": pdflatex_cmd,
        "timeout_s": timeout_s,
        "raster_dpi": raster_dpi,
        "items": [{"expr": s.expr, "png_path": s.png_path, "w": s.w, "h": s.h} for s in samples],
    }
    (outp / "math_bank.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return samples