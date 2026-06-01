# src/ai1_gen/orchestrator/_param_fields_latex.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import List

from .models import ParamField


LATEX_FIELDS: List[ParamField] = [
    ParamField(
        key="latex.enable",
        label="Enable LaTeX",
        group="LaTeX",
        field_type="bool",
        default=True,
        help_text="LaTeX/math üretimini aç/kapat.",
        visibility="advanced",
    ),
    ParamField(
        key="latex.miktex_bin",
        label="MiKTeX Bin",
        group="LaTeX",
        field_type="path",
        default=None,
        help_text="MiKTeX bin klasörü. PATH dışında ise belirt.",
        visibility="advanced",
    ),
    ParamField(
        key="latex.compiler",
        label="LaTeX Compiler",
        group="LaTeX",
        field_type="enum",
        default="pdflatex",
        choices=["pdflatex", "xelatex", "lualatex"],
        help_text="Kullanılacak LaTeX derleyicisi.",
        visibility="advanced",
    ),
    ParamField(
        key="latex.timeout_s",
        label="LaTeX Timeout (s)",
        group="LaTeX",
        field_type="int",
        default=12,
        minimum=1,
        help_text="LaTeX render timeout süresi.",
        visibility="advanced",
    ),
    ParamField(
        key="latex.raster_dpi",
        label="LaTeX Raster DPI",
        group="LaTeX",
        field_type="int",
        default=300,
        minimum=72,
        help_text="LaTeX raster çıktı DPI değeri.",
        visibility="advanced",
    ),
    ParamField(
        key="latex.level",
        label="LaTeX Difficulty",
        group="LaTeX",
        field_type="enum",
        default="medium",
        choices=["clean", "medium", "heavy"],
        help_text="Math expression üretim karmaşıklığı.",
        visibility="advanced",
    ),
    ParamField(
        key="latex.allowed_ops",
        label="Allowed Math Operations",
        group="LaTeX",
        field_type="json",
        default=[
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
        ],
        help_text="İzin verilen math işlem aileleri.",
        visibility="advanced",
    ),
]