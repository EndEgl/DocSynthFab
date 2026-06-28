# src/docsynthfab/orchestrator/_param_fields_render.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import List

from .models import ParamField


RENDER_FIELDS: List[ParamField] = [
    ParamField(
        key="render.text",
        label="Render Text Config",
        group="Render",
        field_type="json",
        default={},
        help_text="Metin render ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="render.non_text",
        label="Render Non-Text Config",
        group="Render",
        field_type="json",
        default={},
        help_text="Non-text render ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="render.latex",
        label="Render Latex Config",
        group="Render",
        field_type="json",
        default={},
        help_text="LaTeX render ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="style",
        label="Style Config",
        group="Render",
        field_type="json",
        default={},
        help_text="Style / contrast / local mode ayarları.",
        visibility="advanced",
    ),
]



