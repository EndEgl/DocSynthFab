# src/ai1_gen/orchestrator/param_schema.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import Dict, List

from .models import ParamField

from ._param_fields_basic import BASIC_FIELDS
from ._param_fields_yaml_manager import YAML_MANAGER_FIELDS
from ._param_fields_run import RUN_FIELDS
from ._param_fields_page import PAGE_FIELDS
from ._param_fields_distribution import DISTRIBUTION_FIELDS
from ._param_fields_layout import LAYOUT_FIELDS
from ._param_fields_content import CONTENT_FIELDS
from ._param_fields_latex import LATEX_FIELDS
from ._param_fields_render import RENDER_FIELDS
from ._param_fields_augment import AUGMENT_FIELDS
from ._param_fields_qc import QC_FIELDS
from ._param_fields_telemetry import TELEMETRY_FIELDS


_PARAM_FIELDS: List[ParamField] = [
    *BASIC_FIELDS,
    *YAML_MANAGER_FIELDS,
    *RUN_FIELDS,
    *PAGE_FIELDS,
    *DISTRIBUTION_FIELDS,
    *LAYOUT_FIELDS,
    *CONTENT_FIELDS,
    *LATEX_FIELDS,
    *RENDER_FIELDS,
    *AUGMENT_FIELDS,
    *QC_FIELDS,
    *TELEMETRY_FIELDS,
]


def get_param_schema() -> List[ParamField]:
    return list(_PARAM_FIELDS)


def get_param_groups(visibility: str | None = None) -> Dict[str, List[ParamField]]:
    out: Dict[str, List[ParamField]] = {}

    for field in _PARAM_FIELDS:
        if visibility is not None and field.visibility != visibility:
            continue

        out.setdefault(field.group, []).append(field)

    return out