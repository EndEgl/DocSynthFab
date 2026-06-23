# src/docsynthfab/orchestrator/_param_fields_layout.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import List

from .models import ParamField


LAYOUT_FIELDS: List[ParamField] = [
    ParamField(
        key="layout.targets",
        label="Layout Targets",
        group="Layout",
        field_type="json",
        default={},
        help_text="Density seviyelerine göre layout hedefleri.",
        visibility="advanced",
    ),
    ParamField(
        key="density_thresholds",
        label="Density Thresholds",
        group="Layout",
        field_type="json",
        default={},
        help_text="Density threshold ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="thresholds",
        label="Legacy Thresholds",
        group="Layout",
        field_type="json",
        default={},
        help_text="Geriye dönük threshold alanı.",
        visibility="advanced",
    ),
    ParamField(
        key="layout.occupancy.enable",
        label="Enable Occupancy Placement",
        group="Layout / Occupancy",
        field_type="bool",
        default=True,
        help_text="RAM-only boşluk/yerleşim motorunu açar. Annotation JSON'a occupancy debug yazılmaz.",
        visibility="advanced",
    ),
    ParamField(
        key="layout.occupancy.whitespace_strategy",
        label="Whitespace Strategy",
        group="Layout / Occupancy",
        field_type="enum",
        default="balanced",
        choices=["airy", "balanced", "compact", "packed"],
        help_text="Sayfa boşluk stratejisi: airy daha boş, packed daha yoğun/stres.",
        visibility="advanced",
    ),
    ParamField(
        key="layout.occupancy.spread_percent",
        label="Content Spread (%)",
        group="Layout / Occupancy",
        field_type="float",
        default=65.0,
        minimum=0.0,
        maximum=100.0,
        step=5.0,
        help_text="İçeriklerin sayfaya ne kadar yayıldığını belirler. 0 kümeli, 100 daha yayılmış.",
        visibility="advanced",
    ),
    ParamField(
        key="layout.occupancy.min_gap_px",
        label="Min Gap Between Blocks (px)",
        group="Layout / Occupancy",
        field_type="int",
        default=12,
        minimum=0,
        maximum=128,
        help_text="Bloklar arası minimum güvenli boşluk. Simple GUI'deki Block gap (%) buraya çevrilir.",
        visibility="advanced",
    ),
    ParamField(
        key="layout.occupancy.max_place_attempts",
        label="Max Placement Attempts",
        group="Layout / Occupancy",
        field_type="int",
        default=48,
        minimum=4,
        maximum=256,
        help_text="Her blok için denenecek candidate pozisyon sayısı. Yüksek değer daha iyi ama daha yavaş olabilir.",
        visibility="advanced",
    ),
    ParamField(
        key="layout.occupancy.target_fill_ratio",
        label="Target Fill Ratio",
        group="Layout / Occupancy",
        field_type="json",
        default={
            "sparse": [0.06, 0.14],
            "normal": [0.14, 0.26],
            "dense": [0.26, 0.42],
            "mixed": [0.12, 0.34],
        },
        help_text="Density seviyelerine göre hedef kaplanan alan oranı. Sadece layout hesaplarında kullanılır.",
        visibility="advanced",
    ),
    ParamField(
        key="layout.anchor.mode",
        label="Anchor Mode",
        group="Layout",
        field_type="enum",
        default="top_left",
        choices=["top_left", "top_center", "center", "custom"],
        help_text="Yerleşim başlangıç noktası modu.",
        visibility="advanced",
    ),
    ParamField(
        key="layout.anchor.x_px",
        label="Anchor X (px)",
        group="Layout",
        field_type="int",
        default=0,
        help_text="Custom anchor için X başlangıç koordinatı.",
        visibility="advanced",
    ),
    ParamField(
        key="layout.anchor.y_px",
        label="Anchor Y (px)",
        group="Layout",
        field_type="int",
        default=0,
        help_text="Custom anchor için Y başlangıç koordinatı.",
        visibility="advanced",
    ),
]



