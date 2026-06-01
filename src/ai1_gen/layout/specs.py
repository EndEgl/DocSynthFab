# src/ai1_gen/layout/specs.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class BlockSpec:
    block_id: int
    block_type: str
    block_order: int
    column_id: int
    bbox: Tuple[int, int, int, int]
    style: Dict[str, object]


@dataclass
class LineSpec:
    line_id: int
    block_id: int
    line_type: str
    line_order_in_block: int
    global_line_order: int
    bbox: Tuple[int, int, int, int]
    quad: Optional[List[Tuple[float, float]]] = None
    is_hard: bool = False


@dataclass
class PageSpec:
    page_id: str
    w: int
    h: int
    dpi: int
    page_size_name: str
    page_width_in: float
    page_height_in: float
    orientation: str
    page_family: str
    layout_type: str
    density_level: str
    scale_profile: str
    noise_level: str
    rotation_deg: float
    perspective: bool
    has_table: bool
    has_equation: bool
    has_figure: bool
    blocks: List[BlockSpec]
    lines: List[LineSpec]