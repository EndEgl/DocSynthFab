# src/docsynthfab/render/latex_rendering.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12

from __future__ import annotations

import random
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw

from docsynthfab.latex.normalize import normalize_latex_expr
from docsynthfab.latex.miktex_render import (
    render_latex_to_rgba,
    sample_latex_expr,
)

from .draw_utils import _draw_text_glyph_mask, _sample_contrast_color
from .font_utils import _fit_font_to_bbox_height


def _fit_rgba_contain(
    img_rgba: Image.Image,
    target_w: int,
    target_h: int,
    *,
    rng: Optional[random.Random] = None,
    random_offset: bool = False,
) -> Image.Image:
    """
    Fit an RGBA image into a target box while preserving aspect ratio.
    """
    target_w = max(1, int(target_w))
    target_h = max(1, int(target_h))

    src_w, src_h = img_rgba.size

    if src_w <= 0 or src_h <= 0:
        return Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))

    scale = min(target_w / src_w, target_h / src_h)

    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))

    resized = img_rgba.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))

    free_x = max(0, target_w - new_w)
    free_y = max(0, target_h - new_h)

    if random_offset and rng is not None:
        off_x = int(rng.uniform(0, free_x)) if free_x > 0 else 0
        off_y = int(rng.uniform(0, free_y)) if free_y > 0 else 0
    else:
        off_x = free_x // 2
        off_y = free_y // 2

    canvas.paste(resized, (off_x, off_y), resized)
    return canvas


def _safe_latex_fallback_candidates() -> list[str]:
    return [
        r"x^2 + y^2 = z^2",
        r"E = mc^2",
        r"a^2 + b^2 = c^2",
        r"\frac{a}{b} + \frac{c}{d}",
        r"\sum_{i=1}^{n} i",
        r"\sqrt{x+1}",
        r"P(A \mid B)=\frac{P(A\cap B)}{P(B)}",
    ]


def _render_latex_with_retries(
    *,
    initial_expr: str,
    rng: random.Random,
    latex_level: str,
    allowed_ops: list[str] | None,
    pdflatex_cmd: str,
    timeout_s: int,
    raster_dpi: int,
    latex_backend: str,
    latex_http_base_url: str,
    target_w: int,
    target_h: int,
    random_offset: bool,
) -> tuple[bool, str, Image.Image | None, list[dict[str, Any]]]:
    """
    Render LaTeX with a safe retry chain.

    Guarantees:
    - On success, returns a real RGBA LaTeX image.
    - On failure, returns collected errors so the caller can use fallback drawing.
    """
    errors: list[dict[str, Any]] = []
    candidates: list[str] = []

    initial_expr = _normalize_latex_expr(str(initial_expr or "").strip())

    if initial_expr:
        candidates.append(initial_expr)

    for _ in range(2):
        try:
            expr = _normalize_latex_expr(
                sample_latex_expr(
                    rng,
                    level=latex_level,
                    allowed_ops=allowed_ops,
                )
            )

            if expr and expr not in candidates:
                candidates.append(expr)

        except Exception as e:
            errors.append({
                "stage": "sample_retry_expr",
                "expr": "",
                "error": repr(e),
            })

    for expr in _safe_latex_fallback_candidates():
        if expr not in candidates:
            candidates.append(expr)

    for attempt, expr in enumerate(candidates, start=1):
        try:
            eq = render_latex_to_rgba(
                expr,
                pdflatex_cmd=pdflatex_cmd,
                timeout_s=timeout_s,
                raster_dpi=raster_dpi,
                backend=latex_backend,
                http_base_url=latex_http_base_url,
            ).convert("RGBA")

            eq = _fit_rgba_contain(
                eq,
                max(10, target_w),
                max(10, target_h),
                rng=rng,
                random_offset=random_offset,
            )

            return True, expr, eq, errors

        except Exception as e:
            errors.append({
                "stage": "render_retry",
                "attempt": attempt,
                "expr": str(expr),
                "error": repr(e),
            })

    return False, initial_expr, None, errors


def _resolve_latex_cfg(render_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize render.latex config.

    In this project, LaTeX rendering is expected to use the Docker HTTP renderer.
    """
    latex_cfg = render_cfg.get("latex", {}) or {}

    backend = str(latex_cfg.get("backend", "http")).strip().lower()

    if backend not in {"http"}:
        backend = "http"

    return {
        "enable": bool(latex_cfg.get("enable", True)),
        "backend": backend,
        "http_base_url": str(latex_cfg.get("http_base_url", "http://127.0.0.1:8080")).strip(),
        "compiler": str(latex_cfg.get("compiler", "pdflatex")),
        "timeout_s": int(latex_cfg.get("timeout_s", 12)),
        "raster_dpi": int(latex_cfg.get("raster_dpi", 300)),
        "level": str(latex_cfg.get("level", "medium")).strip().lower(),
        "allowed_ops": latex_cfg.get("allowed_ops", None),
        "health_check": bool(latex_cfg.get("health_check", False)),
        "draw_fallback_expr": bool(latex_cfg.get("draw_fallback_expr", False)),
    }


def _draw_math_fallback_text(
    draw_img: ImageDraw.ImageDraw,
    draw_mask: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    ww: int,
    hh: int,
    expr: str,
    fonts_dir: str | None,
    base_size: int,
    rng: random.Random,
    style_cfg: Dict[str, Any],
) -> None:
    """
    Draw a small safe math symbol when LaTeX rendering fails.

    The raw LaTeX source is still preserved in gt_latex.
    """
    fallback_text = rng.choice([
        "∑",
        "√x",
        "x²",
        "α+β",
        "A∩B",
        "π",
        "∂f",
        "≤",
        "∞",
    ])

    fnt = _fit_font_to_bbox_height(
        fonts_dir,
        desired_size=max(10, int(min(ww, hh) * 0.70)),
        bbox_h=hh,
        rng=rng,
        script="symbols",
        role="body",
        probe_text="∑ √ ≤ ≥ α β π ∞",
    )

    math_color = _sample_contrast_color(rng, style_cfg)

    _draw_text_glyph_mask(
        draw_img,
        draw_mask,
        x,
        y,
        fallback_text,
        fnt,
        math_color,
    )


def _normalize_latex_expr(expr: str) -> str:
    try:
        return normalize_latex_expr(expr)
    except Exception:
        return r"x+y=0"



