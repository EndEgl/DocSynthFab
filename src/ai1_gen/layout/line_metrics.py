# src/ai1_gen/layout/line_metrics.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random

from .specs import BlockSpec


def _sample_base_pt(rng: random.Random) -> float:
    """Sample a weighted font size between 2 and 48 points."""
    pick = rng.random()

    if pick < 0.05:
        return rng.uniform(2.0, 8.0)

    if pick < 0.70:
        return rng.choice([9.0, 9.5, 10.0, 10.5, 11.0, 11.5])

    if pick < 0.90:
        return rng.uniform(12.0, 20.0)

    return rng.uniform(21.0, 48.0)


def _line_height_px(
    h: int,
    density_level: str,
    dpi: int,
    page_family: str,
    rng: random.Random,
) -> int:
    base_pt = _sample_base_pt(rng)
    base_px = int(base_pt * (dpi / 72.0))

    if density_level == "dense":
        base = int(base_px * 1.15)

    elif density_level == "sparse":
        base = int(base_px * 1.80)

    else:
        base = int(base_px * 1.40)

    if page_family == "notes":
        base = int(base * 0.92)

    elif page_family == "worksheet":
        base = int(base * 0.96)

    return max(10, base)


def _line_type_of_block(block_type: str) -> str:
    if block_type == "equation":
        return "math"

    if block_type == "caption":
        return "caption"

    if block_type == "table":
        return "table_cell"

    return "text"


def _max_lines_in_block(block: BlockSpec, base_lh: int) -> int:
    _, _, _, bh = block.bbox
    return max(1, bh // max(8, base_lh))