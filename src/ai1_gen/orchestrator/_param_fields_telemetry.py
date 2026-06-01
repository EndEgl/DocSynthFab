# src/ai1_gen/orchestrator/_param_fields_telemetry.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import List

from .models import ParamField


TELEMETRY_FIELDS: List[ParamField] = [
    ParamField(
        key="telemetry.mode",
        label="Telemetry Mode",
        group="Telemetry",
        field_type="enum",
        default="single_line",
        choices=["single_line", "multi_line"],
        help_text="İlerleme gösterim modu.",
        visibility="advanced",
    ),
    ParamField(
        key="telemetry.ascii_only",
        label="ASCII Only",
        group="Telemetry",
        field_type="bool",
        default=True,
        help_text="ASCII-only çıktı kullan.",
        visibility="advanced",
    ),
    ParamField(
        key="telemetry.update_interval_s",
        label="Telemetry Update Interval",
        group="Telemetry",
        field_type="float",
        default=1.2,
        minimum=0.1,
        step=0.1,
        help_text="İlerleme güncelleme aralığı.",
        visibility="advanced",
    ),
    ParamField(
        key="telemetry.show_eta",
        label="Show ETA",
        group="Telemetry",
        field_type="bool",
        default=True,
        help_text="ETA göster.",
        visibility="advanced",
    ),
    ParamField(
        key="telemetry.show_rate",
        label="Show Rate",
        group="Telemetry",
        field_type="bool",
        default=True,
        help_text="Üretim hızını göster.",
        visibility="advanced",
    ),
    ParamField(
        key="telemetry.temperature.require_temp_sensor",
        label="Require Temp Sensor",
        group="Telemetry",
        field_type="bool",
        default=True,
        help_text="Sıcaklık sensörü yoksa hata ver.",
        visibility="advanced",
    ),
    ParamField(
        key="telemetry.temperature.prefer_gpu",
        label="Prefer GPU Temperature",
        group="Telemetry",
        field_type="bool",
        default=True,
        help_text="Mümkünse GPU sıcaklığını tercih et.",
        visibility="advanced",
    ),
]