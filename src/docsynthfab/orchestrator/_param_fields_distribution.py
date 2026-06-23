# src/docsynthfab/orchestrator/_param_fields_distribution.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import List

from .models import ParamField


DISTRIBUTION_FIELDS: List[ParamField] = [
    ParamField(
        key="dist.density_dist",
        label="Density Distribution",
        group="Distribution",
        field_type="json",
        default={},
        help_text="Density level dağılımı.",
        visibility="advanced",
    ),
    ParamField(
        key="dist.scale_dist",
        label="Scale Distribution",
        group="Distribution",
        field_type="json",
        default={},
        help_text="Scale profile dağılımı.",
        visibility="advanced",
    ),
    ParamField(
        key="dist.noise_level_dist",
        label="Noise Level Distribution",
        group="Distribution",
        field_type="json",
        default={"clean": 0.3, "medium": 0.5, "heavy": 0.2},
        help_text="Noise level dağılımı.",
        visibility="advanced",
    ),
]



