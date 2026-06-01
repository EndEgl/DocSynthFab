# src/ai1_gen/orchestrator/_param_fields_augment.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import List

from .models import ParamField


AUGMENT_FIELDS: List[ParamField] = [
    ParamField(
        key="augment.selection_policy",
        label="Augment Selection Policy",
        group="Augment",
        field_type="json",
        default={},
        help_text="Noise seviyesine göre augment seçim politikası.",
        visibility="advanced",
    ),
    ParamField(
        key="augment.photometric",
        label="Photometric Config",
        group="Augment",
        field_type="json",
        default={},
        help_text="Photometric augment ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="augment.blur_noise",
        label="Blur Noise Config",
        group="Augment",
        field_type="json",
        default={},
        help_text="Blur/noise augment ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="augment.capture_sim",
        label="Capture Simulation Config",
        group="Augment",
        field_type="json",
        default={},
        help_text="Capture simulation ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="augment.geometry",
        label="Geometry Config",
        group="Augment",
        field_type="json",
        default={},
        help_text="Geometric augment ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="augment.edge_degredation",
        label="Edge Degradation Config",
        group="Augment",
        field_type="json",
        default={},
        help_text="Edge degradation ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="augment.elastic_distortion",
        label="Elastic Distortion Config",
        group="Augment",
        field_type="json",
        default={},
        help_text="Elastic distortion ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="augment.min_area_px",
        label="Augment Min Area PX",
        group="Augment",
        field_type="int",
        default=25,
        minimum=1,
        help_text="Geometry sonrası minimum bbox alanı.",
        visibility="advanced",
    ),
]