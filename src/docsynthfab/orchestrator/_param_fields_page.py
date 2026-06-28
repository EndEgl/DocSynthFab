# src/docsynthfab/orchestrator/_param_fields_page.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import List

from .models import ParamField


PAGE_FIELDS: List[ParamField] = [
    ParamField(
        key="page.size_name",
        label="Legacy Size Name",
        group="Page",
        field_type="str",
        default="A4",
        help_text="Geriye dönük uyumluluk için eski sayfa ismi.",
        visibility="advanced",
    ),
    ParamField(
        key="page.dpi_choices",
        label="DPI Choices",
        group="Page",
        field_type="json",
        default=[200, 300],
        help_text="DPI seçim listesi.",
        visibility="advanced",
    ),
    ParamField(
        key="page.bg_color_rgb",
        label="Background RGB",
        group="Page",
        field_type="color_rgb",
        default=[255, 255, 255],
        help_text="Arka plan rengi.",
        visibility="advanced",
    ),
    ParamField(
        key="page.size_dist",
        label="Page Size Distribution",
        group="Page",
        field_type="json",
        default={},
        help_text="Sayfa boyutu dağılımı.",
        visibility="advanced",
    ),
]



