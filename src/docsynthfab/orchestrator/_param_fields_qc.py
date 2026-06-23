# src/docsynthfab/orchestrator/_param_fields_qc.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import List

from .models import ParamField


QC_FIELDS: List[ParamField] = [
    ParamField(
        key="qc.dist_tolerance_abs",
        label="QC Dist Tolerance",
        group="QC",
        field_type="float",
        default=0.03,
        minimum=0.0,
        maximum=1.0,
        step=0.001,
        help_text="QC dağılım toleransı.",
        visibility="advanced",
    ),
]



