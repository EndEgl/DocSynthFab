# src/ai1_gen/orchestrator/_param_fields_yaml_manager.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import List

from .models import ParamField


YAML_MANAGER_FIELDS: List[ParamField] = [
    ParamField(
        key="ui.yaml_manager.enable_raw_override",
        label="Enable Raw YAML Override",
        group="YAML Manager",
        field_type="bool",
        default=False,
        help_text="Raw YAML override panelini etkinleştirir.",
        visibility="advanced",
    ),
    ParamField(
        key="ui.yaml_manager.allow_export",
        label="Allow YAML Export",
        group="YAML Manager",
        field_type="bool",
        default=True,
        help_text="Mevcut effective config'i YAML olarak dışa aktarmaya izin verir.",
        visibility="advanced",
    ),
    ParamField(
        key="ui.yaml_manager.allow_reset_to_baseline",
        label="Allow Reset To Baseline",
        group="YAML Manager",
        field_type="bool",
        default=True,
        help_text="GUI'de baseline/default YAML'a dönme butonunu etkinleştirir.",
        visibility="advanced",
    ),
    ParamField(
        key="ui.yaml_manager.show_effective_preview",
        label="Show Effective YAML Preview",
        group="YAML Manager",
        field_type="bool",
        default=True,
        help_text="Effective config önizleme alanını gösterir.",
        visibility="advanced",
    ),
]