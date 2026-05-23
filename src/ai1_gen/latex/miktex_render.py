# src/ai1_gen/latex/miktex_render.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - Pillow>=10,<12
# - requests>=2.31,<3.0
#
# External runtime:
# - Docker container içinde çalışan LaTeX HTTP renderer gerekir.
# - pypdfium2, pdflatex ve MiKTeX ana Python ortamında kullanılmaz.
# - pypdfium2 ve MiKTeX sadece docker/latex image içinde bulunur.

from __future__ import annotations

import base64
import json
import random
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Set
import os

from ai1_gen.latex.docker_runtime import (
    LatexDockerRuntimeError,
    ensure_latex_container,
)

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


def _render_latex_to_rgba_http(
    latex_expr: str,
    *,
    http_base_url: str = "http://127.0.0.1:8080",
    timeout_s: int = 12,
    raster_dpi: int = 300,
) -> Image.Image:
    """
    Docker içindeki HTTP LaTeX renderer'a istek atar.
    Beklenen endpoint:
    - GET  /health
    - POST /render
    """
    try:
        import requests
    except Exception as e:
        raise LatexRenderError("render/latex-http-missing: requests import edilemedi") from e

    auto_docker = str(
        os.environ.get("AI1_LATEX_AUTO_DOCKER", "1")
    ).strip().lower() not in {"0", "false", "no", "off"}

    if auto_docker:
        try:
            ensure_latex_container(
                http_base_url=http_base_url,
                container_name=os.environ.get(
                    "AI1_LATEX_CONTAINER_NAME",
                    "ai1_gen_latex_renderer",
                ),
                image_name=os.environ.get(
                    "AI1_LATEX_IMAGE",
                    "ai1-gen-latex-renderer:latest",
                ),


                host_port=int(os.environ.get("AI1_LATEX_HOST_PORT", "8080")),
                container_port=int(os.environ.get("AI1_LATEX_CONTAINER_PORT", "8080")),
                build_if_missing=True,
                force_recreate_if_unhealthy=True,
            )
        except LatexDockerRuntimeError as e:
            raise LatexRenderError(f"render/latex-docker-runtime-failed: {e}") from e

    url = f"{http_base_url.rstrip('/')}/render"

    payload: Dict[str, Any] = {
        "expr": latex_expr,
        "dpi": int(raster_dpi),
        "timeout_s": int(timeout_s),
    }

    try:
        resp = requests.post(url, json=payload, timeout=float(timeout_s) + 10.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise LatexRenderError(
            f"render/latex-http-unreachable: LaTeX HTTP renderer erişilemedi: {url}"
        ) from e

    if not bool(data.get("ok", False)):
        err = data.get("error", "unknown")
        stdout = str(data.get("stdout", "") or "")
        stderr = str(data.get("stderr", "") or "")
        raise LatexRenderError(
            "render/latex-http-failed: "
            f"{err}\nstdout={stdout[-1200:]}\nstderr={stderr[-1200:]}"
        )

    png_b64 = data.get("png_base64")
    if not png_b64:
        raise LatexRenderError("render/latex-http-empty-response: png_base64 yok")

    try:
        png_bytes = base64.b64decode(png_b64)
        img = Image.open(BytesIO(png_bytes)).convert("RGBA")
    except Exception as e:
        raise LatexRenderError("render/latex-http-decode-failed") from e

    return _crop_rgba_to_alpha_bbox(img, pad=4)


def render_latex_to_rgba(
    latex_expr: str,
    *,
    pdflatex_cmd: str = "pdflatex",  # backward compatibility, kullanılmıyor
    timeout_s: int = 12,
    raster_dpi: int = 300,
    backend: str = "http",
    http_base_url: str = "http://127.0.0.1:8080",
) -> Image.Image:
    """
    LaTeX render ana giriş noktası.

    Bu paketleme sürümünde render işlemi sadece Docker HTTP renderer üzerinden yapılır.
    pdflatex/pypdfium2/MiKTeX ana Python ortamında kullanılmaz.

    Not:
    - pdflatex_cmd parametresi eski çağrılar kırılmasın diye korunmuştur.
    - backend parametresi eski çağrılar kırılmasın diye korunmuştur.
    - backend yalnızca "http" olabilir.
    """
    backend = (backend or "http").strip().lower()

    if backend != "http":
        raise LatexRenderError(
            f"render/latex-unsupported-backend: {backend}. "
            "Bu sürümde sadece Docker HTTP renderer backend='http' desteklenir."
        )

    return _render_latex_to_rgba_http(
        latex_expr,
        http_base_url=http_base_url,
        timeout_s=timeout_s,
        raster_dpi=raster_dpi,
    )


def check_latex_http_health(
    *,
    http_base_url: str = "http://127.0.0.1:8080",
    timeout_s: float = 5.0,
) -> bool:
    """
    Docker LaTeX HTTP renderer çalışıyor mu kontrol eder.
    """
    try:
        import requests

        url = f"{http_base_url.rstrip('/')}/health"
        resp = requests.get(url, timeout=timeout_s)
        resp.raise_for_status()
        data = resp.json()
        return bool(data.get("ok", False))
    except Exception:
        return False


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
    "derivative",
    "limit",
    "taylor_series",
    "sum_product",
    "matrix",
    "determinant",
    "system",
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

    if "derivative" in allowed:
        v = rng.choice(_VARS)
        f = rng.choice([
            f"{v}^{{{_rand_int(rng, 2, 5)}}}",
            f"\\sin({v})",
            f"\\cos({v})",
            f"e^{{{v}}}",
            f"\\ln({v})",
        ])
        templates.append(r"\frac{d}{d" + v + r"}\left(" + f + r"\right)")
        templates.append(r"\frac{\partial}{\partial " + v + r"}\left(" + f + r"\right)")
        templates.append(r"f'(" + v + r")=" + _expr(rng, 0, 2, list(allowed)))

    if "limit" in allowed:
        v = rng.choice(["x", "n", "t"])
        target = rng.choice(["0", "1", r"\infty"])
        templates.append(
            r"\lim_{" + v + r"\to " + target + r"} "
            + _expr(rng, 0, 2, list(allowed))
        )
        templates.append(
            r"\lim_{" + v + r"\to 0} \frac{\sin " + v + r"}{" + v + r"} = 1"
        )

    if "taylor_series" in allowed:
        v = rng.choice(["x", "t"])
        templates.append(
            r"e^{" + v + r"} = \sum_{n=0}^{\infty} \frac{"
            + v + r"^n}{n!}"
        )
        templates.append(
            r"\sin " + v + r" = \sum_{n=0}^{\infty} "
            r"(-1)^n \frac{" + v + r"^{2n+1}}{(2n+1)!}"
        )
        templates.append(
            r"\cos " + v + r" = \sum_{n=0}^{\infty} "
            r"(-1)^n \frac{" + v + r"^{2n}}{(2n)!}"
        )
        templates.append(
            r"f(" + v + r") \approx f(a) + f'(a)(" + v + r"-a)"
            r" + \frac{f''(a)}{2!}(" + v + r"-a)^2"
        )


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
    
    if "determinant" in allowed:
        templates.append(
            r"\det(A)=\begin{vmatrix} "
            + " & ".join([_expr(rng, 0, 1, list(allowed)) for _ in range(2)]) + r"\\"
            + " & ".join([_expr(rng, 0, 1, list(allowed)) for _ in range(2)])
            + r" \end{vmatrix}"
        )

    if "system" in allowed:
        x, y = rng.choice(["x", "u"]), rng.choice(["y", "v"])
        templates.append(
            r"\begin{cases} "
            + f"{_rand_int(rng, 1, 5)}{x} + {_rand_int(rng, 1, 5)}{y}"
            + f" = {_rand_int(rng, 1, 20)}"
            + r" \\ "
            + f"{_rand_int(rng, 1, 5)}{x} - {_rand_int(rng, 1, 5)}{y}"
            + f" = {_rand_int(rng, 1, 20)}"
            + r" \end{cases}"
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
    backend: str = "http",
    http_base_url: str = "http://127.0.0.1:8080",
) -> List[MathSample]:
    """
    Belirli miktarda matematik PNG üretir.
    - out_dir içine: eq_000001.png ... + math_bank.json
    """
    backend = (backend or "http").strip().lower()
    if backend != "http":
        raise LatexRenderError(
            f"render/latex-unsupported-backend: {backend}. "
            "Bu sürümde sadece Docker HTTP renderer backend='http' desteklenir."
        )

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
            backend="http",
            http_base_url=http_base_url,
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
        "pdflatex_cmd": None,
        "timeout_s": timeout_s,
        "raster_dpi": raster_dpi,
        "level": level,
        "allowed_ops": allowed_ops or _ALLOWED_OPS_DEFAULT,
        "backend": "http",
        "http_base_url": http_base_url,
        "items": [{"expr": s.expr, "png_path": s.png_path, "w": s.w, "h": s.h} for s in samples],
    }

    (outp / "math_bank.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return samples