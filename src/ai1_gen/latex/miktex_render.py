# src/ai1_gen/latex/miktex_render.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - Pillow>=10,<12
# - pypdfium2>=4,<5  (PDF rasterize için)

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


def _crop_rgba_to_alpha_bbox(img: Image.Image, pad: int = 4) -> Image.Image:
    """
    Transparan kenarları kırpıp minik bir padding ile geri döndürür.
    Bu sayede equation aynı hedef bbox içine daha büyük oturur.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise LatexRenderError("render/latex-empty-alpha")

    cropped = img.crop(bbox)

    if pad <= 0:
        return cropped

    out = Image.new(
        "RGBA",
        (cropped.width + 2 * pad, cropped.height + 2 * pad),
        (0, 0, 0, 0),
    )
    out.paste(cropped, (pad, pad), cropped)
    return out


def render_latex_to_rgba(
    latex_expr: str,
    *,
    pdflatex_cmd: str = "pdflatex",
    timeout_s: int = 12,
    raster_dpi: int = 300,
) -> Image.Image:
    """
    pdflatex ile tek sayfalık PDF üretir, pypdfium2 ile rasterize edip
    kırpılmış RGBA döndürür.
    """
    try:
        import pypdfium2 as pdfium
    except Exception as e:
        raise LatexRenderError("render/latex-missing: pypdfium2 import edilemedi") from e

    tex = r"""
\documentclass[12pt]{article}
\usepackage[margin=1pt]{geometry}
\usepackage{amsmath,amssymb}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\begin{document}
\noindent
$\displaystyle %s$
\end{document}
""" % latex_expr

    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        tex_path = td_p / "eq.tex"
        tex_path.write_text(tex, encoding="utf-8")

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

        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
            page = pdf[0]

            scale = float(raster_dpi) / 72.0

            # maybe_alpha=True: sayfada transparency varsa alpha’lı bitmap seçebilir.
            # fill_color=(0,0,0,0): boş arka planı transparan tutmaya çalışır.
            bitmap = page.render(
                scale=scale,
                maybe_alpha=True,
                fill_color=(0, 0, 0, 0),
            )
            img = bitmap.to_pil()

            if img.mode != "RGBA":
                img = img.convert("RGBA")

        except Exception as e:
            raise LatexRenderError("render/pdf-raster-failed") from e
        finally:
            try:
                page.close()
            except Exception:
                pass
            try:
                pdf.close()
            except Exception:
                pass

        img = _crop_rgba_to_alpha_bbox(img, pad=4)
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
_VARS = ["x", "y", "z", "t", "n", "k", "i", "j", "a", "b", "c"]
_FUNCS = ["\\sin", "\\cos", "\\tan", "\\log", "\\ln", "\\exp"]
_ALLOWED_OPS_DEFAULT = [
    "add_sub",
    "multiply",
    "fraction",
    "power",
    "root",
    "trig",
    "log_exp",
    "integral",
    "sum_product",
    "matrix",
    "probability",
    "set",
    "piecewise",
]


def _rand_int(rng: random.Random, a: int, b: int) -> int:
    return rng.randint(a, b)


def _atom(rng: random.Random, allowed_ops: List[str] | None = None) -> str:
    allowed = set(allowed_ops or _ALLOWED_OPS_DEFAULT)

    p = rng.random()
    if p < 0.25:
        return str(_rand_int(rng, 1, 9))
    if p < 0.55:
        return rng.choice(_VARS)
    if p < 0.75:
        return f"\\{rng.choice(_GREEK)}"

    func_pool = []
    if "trig" in allowed:
        func_pool.extend(["\\sin", "\\cos", "\\tan"])
    if "log_exp" in allowed:
        func_pool.extend(["\\log", "\\ln", "\\exp"])

    if not func_pool:
        return rng.choice(_VARS)

    f = rng.choice(func_pool)
    v = rng.choice(_VARS)
    return f"{f}({v})"



def _expr(
    rng: random.Random,
    depth: int = 0,
    max_depth: int = 2,
    allowed_ops: List[str] | None = None,
) -> str:
    allowed = set(allowed_ops or _ALLOWED_OPS_DEFAULT)

    if depth >= max_depth:
        return _atom(rng, list(allowed))

    choices: List[str] = []

    if "add_sub" in allowed:
        choices.append("add_sub")
    if "multiply" in allowed:
        choices.append("multiply")
    if "fraction" in allowed:
        choices.append("fraction")
    if "power" in allowed:
        choices.append("power")
    if "root" in allowed:
        choices.append("root")

    # trig/log_exp atom seviyesinde çalışıyor ama expr boş kalmasın
    if not choices:
        return _atom(rng, list(allowed))

    op = rng.choice(choices)

    if op == "add_sub":
        left = _expr(rng, depth + 1, max_depth, list(allowed))
        right = _expr(rng, depth + 1, max_depth, list(allowed))
        sym = rng.choice(["+", "-"])
        return f"{left} {sym} {right}"

    if op == "multiply":
        left = _expr(rng, depth + 1, max_depth, list(allowed))
        right = _expr(rng, depth + 1, max_depth, list(allowed))
        return f"{left} \\cdot {right}"

    if op == "fraction":
        num = _expr(rng, depth + 1, max_depth, list(allowed))
        den = _expr(rng, depth + 1, max_depth, list(allowed))
        return f"\\frac{{{num}}}{{{den}}}"

    if op == "power":
        base = _atom(rng, list(allowed))
        exp = rng.choice([str(_rand_int(rng, 2, 5)), rng.choice(_VARS), f"\\{rng.choice(_GREEK)}"])
        return f"{base}^{{{exp}}}"

    if op == "root":
        inside = _expr(rng, depth + 1, max_depth, list(allowed))
        if rng.random() < 0.25:
            k = rng.choice([3, 4])
            return f"\\sqrt[{k}]{{{inside}}}"
        return f"\\sqrt{{{inside}}}"

    return _atom(rng, list(allowed))




def _template_equation(rng: random.Random, allowed_ops: List[str] | None = None) -> str:
    allowed = set(allowed_ops or _ALLOWED_OPS_DEFAULT)
    templates: List[str] = []

    if "integral" in allowed:
        templates.append(r"\int_{0}^{1} " + _expr(rng, 0, 2, list(allowed)) + r"\, dx")

    if "sum_product" in allowed:
        templates.append(r"\sum_{i=1}^{n} " + _expr(rng, 0, 2, list(allowed)))
        templates.append(r"\prod_{k=1}^{n}\left(1+\frac{1}{k}\right)")

    if "matrix" in allowed:
        templates.append(
            r"\mathbf{v}=\begin{bmatrix} "
            + " \\\\ ".join([_expr(rng, 0, 1, list(allowed)) for _ in range(3)])
            + r" \end{bmatrix}"
        )
        templates.append(
            r"A=\begin{bmatrix} "
            + " & ".join([_expr(rng, 0, 1, list(allowed)) for _ in range(3)]) + r"\\"
            + " & ".join([_expr(rng, 0, 1, list(allowed)) for _ in range(3)]) + r" \end{bmatrix}"
        )

    if "probability" in allowed:
        templates.append(r"P(A\mid B)=\frac{P(A\cap B)}{P(B)}")

    if "set" in allowed:
        templates.append(r"A=\{x\in\mathbb{R}:\; x>" + str(_rand_int(rng, 0, 3)) + r"\}")

    if "piecewise" in allowed:
        templates.append(
            r"f(x)=\begin{cases} "
            + _expr(rng, 0, 1, list(allowed)) + r", & x\ge 0 \\ "
            + _expr(rng, 0, 1, list(allowed)) + r", & x<0 \end{cases}"
        )

    if "add_sub" in allowed or "multiply" in allowed or "fraction" in allowed or "power" in allowed or "root" in allowed:
        templates.append(_expr(rng, 0, 3, list(allowed)))

    if not templates:
        return _expr(rng, 0, 2, list(_ALLOWED_OPS_DEFAULT))

    return rng.choice(templates)



def sample_latex_expr(
    rng: random.Random,
    *,
    level: str = "medium",
    allowed_ops: List[str] | None = None,
) -> str:
    level = (level or "medium").strip().lower()
    allowed = allowed_ops or _ALLOWED_OPS_DEFAULT

    if level == "clean":
        return _expr(rng, 0, 2, allowed) if rng.random() < 0.6 else _template_equation(rng, allowed)
    if level == "heavy":
        return _template_equation(rng, allowed) if rng.random() < 0.35 else _expr(rng, 0, 4, allowed)
    return _template_equation(rng, allowed) if rng.random() < 0.45 else _expr(rng, 0, 3, allowed)





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
    level: str = "medium",
    allowed_ops: List[str] | None = None,
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

        expr = sample_latex_expr(rng, level=level, allowed_ops=allowed_ops)

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
        "level": level,
        "allowed_ops": allowed_ops or _ALLOWED_OPS_DEFAULT,
        "items": [{"expr": s.expr, "png_path": s.png_path, "w": s.w, "h": s.h} for s in samples],
    }
        

    (outp / "math_bank.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return samples