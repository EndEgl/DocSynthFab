# src/docsynthfab/latex/expression_bank.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set


@dataclass(frozen=True)
class MathSample:
    expr: str
    png_path: str
    w: int
    h: int


GREEK = ["alpha", "beta", "gamma", "delta", "theta", "lambda", "mu", "sigma", "phi", "omega"]
VARS = ["x", "y", "z", "t", "n", "k", "i", "j", "a", "b", "c"]

ALLOWED_OPS_DEFAULT = [
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
    allowed = set(allowed_ops or ALLOWED_OPS_DEFAULT)

    p = rng.random()

    if p < 0.25:
        return str(_rand_int(rng, 1, 9))

    if p < 0.55:
        return rng.choice(VARS)

    if p < 0.75:
        return f"\\{rng.choice(GREEK)}"

    func_pool = []

    if "trig" in allowed:
        func_pool.extend(["\\sin", "\\cos", "\\tan"])

    if "log_exp" in allowed:
        func_pool.extend(["\\log", "\\ln", "\\exp"])

    if not func_pool:
        return rng.choice(VARS)

    func = rng.choice(func_pool)
    var = rng.choice(VARS)
    return f"{func}({var})"


def _expr(
    rng: random.Random,
    depth: int = 0,
    max_depth: int = 2,
    allowed_ops: List[str] | None = None,
) -> str:
    allowed = set(allowed_ops or ALLOWED_OPS_DEFAULT)

    if depth >= max_depth:
        return _atom(rng, list(allowed))

    choices: List[str] = []

    for op in ("add_sub", "multiply", "fraction", "power", "root"):
        if op in allowed:
            choices.append(op)

    if not choices:
        return _atom(rng, list(allowed))

    op = rng.choice(choices)

    if op == "add_sub":
        left = _expr(rng, depth + 1, max_depth, list(allowed))
        right = _expr(rng, depth + 1, max_depth, list(allowed))
        symbol = rng.choice(["+", "-"])
        return f"{left} {symbol} {right}"

    if op == "multiply":
        left = _expr(rng, depth + 1, max_depth, list(allowed))
        right = _expr(rng, depth + 1, max_depth, list(allowed))
        return f"{left} \\cdot {right}"

    if op == "fraction":
        numerator = _expr(rng, depth + 1, max_depth, list(allowed))
        denominator = _expr(rng, depth + 1, max_depth, list(allowed))
        return f"\\frac{{{numerator}}}{{{denominator}}}"

    if op == "power":
        base = _atom(rng, list(allowed))
        exponent = rng.choice(
            [
                str(_rand_int(rng, 2, 5)),
                rng.choice(VARS),
                f"\\{rng.choice(GREEK)}",
            ]
        )
        return f"{base}^{{{exponent}}}"

    if op == "root":
        inside = _expr(rng, depth + 1, max_depth, list(allowed))

        if rng.random() < 0.25:
            degree = rng.choice([3, 4])
            return f"\\sqrt[{degree}]{{{inside}}}"

        return f"\\sqrt{{{inside}}}"

    return _atom(rng, list(allowed))


def _template_equation(rng: random.Random, allowed_ops: List[str] | None = None) -> str:
    allowed = set(allowed_ops or ALLOWED_OPS_DEFAULT)
    templates: List[str] = []

    if "integral" in allowed:
        templates.append(r"\int_{0}^{1} " + _expr(rng, 0, 2, list(allowed)) + r"\, dx")

    if "derivative" in allowed:
        var = rng.choice(VARS)
        func = rng.choice(
            [
                f"{var}^{{{_rand_int(rng, 2, 5)}}}",
                f"\\sin({var})",
                f"\\cos({var})",
                f"e^{{{var}}}",
                f"\\ln({var})",
            ]
        )
        templates.append(r"\frac{d}{d" + var + r"}\left(" + func + r"\right)")
        templates.append(r"\frac{\partial}{\partial " + var + r"}\left(" + func + r"\right)")
        templates.append(r"f'(" + var + r")=" + _expr(rng, 0, 2, list(allowed)))

    if "limit" in allowed:
        var = rng.choice(["x", "n", "t"])
        target = rng.choice(["0", "1", r"\infty"])
        templates.append(
            r"\lim_{"
            + var
            + r"\to "
            + target
            + r"} "
            + _expr(rng, 0, 2, list(allowed))
        )
        templates.append(r"\lim_{" + var + r"\to 0} \frac{\sin " + var + r"}{" + var + r"} = 1")

    if "taylor_series" in allowed:
        var = rng.choice(["x", "t"])
        templates.append(r"e^{" + var + r"} = \sum_{n=0}^{\infty} \frac{" + var + r"^n}{n!}")
        templates.append(
            r"\sin "
            + var
            + r" = \sum_{n=0}^{\infty} (-1)^n \frac{"
            + var
            + r"^{2n+1}}{(2n+1)!}"
        )
        templates.append(
            r"\cos "
            + var
            + r" = \sum_{n=0}^{\infty} (-1)^n \frac{"
            + var
            + r"^{2n}}{(2n)!}"
        )

    if "sum_product" in allowed:
        templates.append(r"\sum_{i=1}^{n} " + _expr(rng, 0, 2, list(allowed)))
        templates.append(r"\prod_{k=1}^{n}\left(1+\frac{1}{k}\right)")

    if "matrix" in allowed:
        templates.append(
            r"\mathbf{v}=\begin{bmatrix} "
            + r" \\ ".join([_expr(rng, 0, 1, list(allowed)) for _ in range(3)])
            + r" \end{bmatrix}"
        )
        templates.append(
            r"A=\begin{bmatrix} "
            + " & ".join([_expr(rng, 0, 1, list(allowed)) for _ in range(3)])
            + r"\\"
            + " & ".join([_expr(rng, 0, 1, list(allowed)) for _ in range(3)])
            + r" \end{bmatrix}"
        )

    if "determinant" in allowed:
        templates.append(
            r"\det(A)=\begin{vmatrix} "
            + " & ".join([_expr(rng, 0, 1, list(allowed)) for _ in range(2)])
            + r"\\"
            + " & ".join([_expr(rng, 0, 1, list(allowed)) for _ in range(2)])
            + r" \end{vmatrix}"
        )

    if "system" in allowed:
        x_var, y_var = rng.choice(["x", "u"]), rng.choice(["y", "v"])
        templates.append(
            r"\begin{cases} "
            + f"{_rand_int(rng, 1, 5)}{x_var} + {_rand_int(rng, 1, 5)}{y_var}"
            + f" = {_rand_int(rng, 1, 20)}"
            + r" \\ "
            + f"{_rand_int(rng, 1, 5)}{x_var} - {_rand_int(rng, 1, 5)}{y_var}"
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
            + _expr(rng, 0, 1, list(allowed))
            + r", & x\ge 0 \\ "
            + _expr(rng, 0, 1, list(allowed))
            + r", & x<0 \end{cases}"
        )

    if {"add_sub", "multiply", "fraction", "power", "root"} & allowed:
        templates.append(_expr(rng, 0, 3, list(allowed)))

    if not templates:
        return _expr(rng, 0, 2, list(ALLOWED_OPS_DEFAULT))

    return rng.choice(templates)


def sample_latex_expr(
    rng: random.Random,
    *,
    level: str = "medium",
    allowed_ops: List[str] | None = None,
) -> str:
    level = (level or "medium").strip().lower()
    allowed = allowed_ops or ALLOWED_OPS_DEFAULT

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
    Generate a rendered math expression bank.

    The output directory receives:
    - eq_000001.png, eq_000002.png, ...
    - math_bank.json

    Runtime behavior:
    - HTTP backend only.
    - Failed LaTeX renders are skipped, not retried forever.
    - Progress is printed so stalled generation can be diagnosed.
    """
    selected_backend = (backend or "http").strip().lower()

    if selected_backend != "http":
        from .errors import LatexRenderError

        raise LatexRenderError(
            f"render/latex-unsupported-backend: {selected_backend}. "
            "Only backend='http' is supported in this release."
        )

    from .errors import LatexRenderError
    from .miktex_render import render_latex_to_rgba

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    seen: Set[str] = set()
    samples: List[MathSample] = []

    tries = 0
    failed = 0
    duplicate_skips = 0

    print(
        f"[MATH_BANK] start target={count} seed={seed} "
        f"level={level!r} backend={selected_backend!r} out_dir={out_path}",
        flush=True,
    )

    while len(samples) < count and tries < max_tries:
        tries += 1

        expr = sample_latex_expr(
            rng,
            level=level,
            allowed_ops=allowed_ops,
        )

        if unique and expr in seen:
            duplicate_skips += 1

            if duplicate_skips % 100 == 0:
                print(
                    f"[MATH_BANK] duplicate_skips={duplicate_skips} "
                    f"current={len(samples)}/{count} tries={tries}/{max_tries}",
                    flush=True,
                )

            continue

        seen.add(expr)

        print(
            f"[MATH_BANK] render_try current={len(samples)}/{count} "
            f"tries={tries}/{max_tries} expr={expr[:160]!r}",
            flush=True,
        )

        try:
            image = render_latex_to_rgba(
                expr,
                pdflatex_cmd=pdflatex_cmd,
                timeout_s=timeout_s,
                raster_dpi=raster_dpi,
                backend="http",
                http_base_url=http_base_url,
            )

        except Exception as exc:
            failed += 1

            print(
                f"[MATH_BANK] render_failed current={len(samples)}/{count} "
                f"tries={tries}/{max_tries} failed={failed} "
                f"error={type(exc).__name__}: {exc}",
                flush=True,
            )

            # Continue with a new expression.
            # This prevents one bad LaTeX expression from blocking the whole run.
            continue

        if image.width <= 1 or image.height <= 1:
            failed += 1

            print(
                f"[MATH_BANK] render_empty current={len(samples)}/{count} "
                f"tries={tries}/{max_tries} size={image.width}x{image.height} "
                f"expr={expr[:160]!r}",
                flush=True,
            )

            continue

        index = len(samples) + 1
        filename = f"eq_{index:06d}.png"
        path = out_path / filename

        try:
            image.save(path, format="PNG", optimize=False)

        except Exception as exc:
            failed += 1

            print(
                f"[MATH_BANK] save_failed index={index} path={path} "
                f"error={type(exc).__name__}: {exc}",
                flush=True,
            )

            continue

        sample = MathSample(
            expr=expr,
            png_path=str(path),
            w=image.width,
            h=image.height,
        )

        samples.append(sample)

        print(
            f"[MATH_BANK] saved index={index} "
            f"current={len(samples)}/{count} path={path} "
            f"size={image.width}x{image.height}",
            flush=True,
        )

    if len(samples) < count:
        print(
            f"[MATH_BANK] incomplete target={count} produced={len(samples)} "
            f"tries={tries}/{max_tries} failed={failed} "
            f"duplicate_skips={duplicate_skips}",
            flush=True,
        )

    metadata = {
        "version": "docsynthfab-ds-v0.1",
        "seed": seed,
        "requested_count": count,
        "count": len(samples),
        "tries": tries,
        "failed": failed,
        "duplicate_skips": duplicate_skips,
        "pdflatex_cmd": None,
        "timeout_s": timeout_s,
        "raster_dpi": raster_dpi,
        "level": level,
        "allowed_ops": allowed_ops or ALLOWED_OPS_DEFAULT,
        "backend": "http",
        "http_base_url": http_base_url,
        "items": [
            {
                "expr": sample.expr,
                "png_path": sample.png_path,
                "w": sample.w,
                "h": sample.h,
            }
            for sample in samples
        ],
    }

    (out_path / "math_bank.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"[MATH_BANK] done produced={len(samples)}/{count} "
        f"metadata={out_path / 'math_bank.json'}",
        flush=True,
    )

    return samples



