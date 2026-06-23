# src/docsynthfab/latex/miktex_render.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12
# - requests>=2.31,<3.0

from __future__ import annotations

from PIL import Image

from .errors import LatexRenderError
from .expression_bank import MathSample, generate_math_bank, sample_latex_expr
from .http_render import check_latex_http_health, render_latex_to_rgba_http
from .normalize import normalize_latex_expr


def render_latex_to_rgba(
    latex_expr: str,
    *,
    pdflatex_cmd: str = "pdflatex",
    timeout_s: int = 12,
    raster_dpi: int = 300,
    backend: str = "http",
    http_base_url: str = "http://127.0.0.1:8080",
) -> Image.Image:
    """
    Public LaTeX render entry point.

    This release renders only through the Docker HTTP renderer. The
    pdflatex_cmd and backend parameters are kept for backward compatibility.
    """
    selected_backend = (backend or "http").strip().lower()

    if selected_backend != "http":
        raise LatexRenderError(
            f"render/latex-unsupported-backend: {selected_backend}. "
            "Only backend='http' is supported in this release."
        )

    return render_latex_to_rgba_http(
        latex_expr,
        http_base_url=http_base_url,
        timeout_s=timeout_s,
        raster_dpi=raster_dpi,
    )


__all__ = [
    "MathSample",
    "LatexRenderError",
    "render_latex_to_rgba",
    "generate_math_bank",
    "sample_latex_expr",
    "check_latex_http_health",
    "normalize_latex_expr",
]



