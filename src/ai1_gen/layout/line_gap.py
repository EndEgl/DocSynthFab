# src/ai1_gen/layout/line_gap.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import Tuple


def _apply_line_gap_randomness(
    bbox: Tuple[int, int, int, int],
    *,
    block_y: int,
    block_h: int,
    line_index: int,
    line_count: int,
    line_h: int,
    scale: float,
    density_level: str,
    block_type: str,
    rng: random.Random,
) -> Tuple[int, int, int, int]:
    """
    Apply controlled line-gap randomness inside a block.

    scale=0 keeps the old fixed behavior. Higher values add more natural
    vertical variation while limiting damage on dense pages.
    """
    if scale <= 0:
        return bbox

    x, y, w, h = bbox
    safe_scale = max(0.0, min(float(scale), 3.0))

    if density_level in {"dense", "very_dense"}:
        safe_scale *= 0.55

    elif density_level == "sparse":
        safe_scale *= 1.20

    if block_type == "title":
        safe_scale *= 0.20

    elif block_type == "caption":
        safe_scale *= 0.40

    elif block_type == "equation":
        safe_scale *= 0.30

    elif block_type == "list":
        safe_scale *= 0.70

    elif block_type == "table":
        safe_scale *= 0.0

    if safe_scale <= 0:
        return bbox

    if line_index == 0:
        safe_scale *= 0.35

    if line_count <= 2:
        safe_scale *= 0.45

    max_extra = int(max(0, line_h * 0.35 * safe_scale))

    if max_extra <= 0:
        return bbox

    dy = rng.randint(-max(1, max_extra // 4), max_extra)

    if line_index > 0 and rng.random() < min(0.18 * safe_scale, 0.45):
        dy += rng.randint(0, max_extra)

    y2 = y + dy
    block_bottom = block_y + block_h
    y2 = max(block_y, min(y2, block_bottom - h))

    return int(x), int(y2), int(w), int(h)