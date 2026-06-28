# src/docsynthfab/layout/line_bboxes.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import Tuple


def _paragraph_line_bbox(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    line_index: int,
    line_count: int,
    line_h: int,
    rng: random.Random,
) -> Tuple[int, int, int, int]:
    y = by + int(0.10 * bh) + line_index * line_h
    xpad = int(0.03 * bw)

    if line_index == 0 and rng.random() < 0.72:
        xpad += int(0.05 * bw)

    if line_index == line_count - 1 and line_count > 1:
        line_w = int(bw * rng.uniform(0.35, 0.76))

    else:
        if rng.random() < 0.52:
            line_w = int((bw - xpad) * rng.uniform(0.96, 1.00))
        else:
            line_w = int((bw - xpad) * rng.uniform(0.88, 0.95))

    line_w = max(12, min(line_w, bw - xpad - 4))
    actual_line_h = max(6, line_h - int(0.30 * line_h))

    x = bx + xpad
    y = y + int(0.15 * line_h)

    return x, y, line_w, actual_line_h


def _list_line_bbox(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    line_index: int,
    line_h: int,
    rng: random.Random,
) -> Tuple[int, int, int, int]:
    y = by + int(0.10 * bh) + line_index * line_h
    xpad = int(0.03 * bw) + int(0.04 * bw)
    line_w = int((bw - xpad) * rng.uniform(0.82, 0.95))

    line_w = max(12, min(line_w, bw - xpad - 4))
    actual_line_h = max(6, line_h - int(0.30 * line_h))

    x = bx + xpad
    y = y + int(0.15 * line_h)

    return x, y, line_w, actual_line_h


def _title_line_bbox(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    line_h: int,
    rng: random.Random,
) -> Tuple[int, int, int, int]:
    xpad = int(0.02 * bw)
    line_w = int((bw - xpad) * rng.uniform(0.45, 0.82))

    line_w = max(18, min(line_w, bw - xpad - 4))
    actual_line_h = max(8, line_h - int(0.22 * line_h))

    x = bx + xpad
    y = by + int(0.12 * bh)

    return x, y, line_w, actual_line_h


def _caption_line_bbox(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    line_h: int,
    rng: random.Random,
) -> Tuple[int, int, int, int]:
    xpad = int(0.01 * bw)
    line_w = int((bw - xpad) * rng.uniform(0.55, 0.96))

    line_w = max(16, min(line_w, bw - xpad - 4))
    actual_line_h = max(6, line_h - int(0.30 * line_h))

    x = bx + xpad
    y = by + int(0.10 * bh)

    return x, y, line_w, actual_line_h


def _equation_line_bbox(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    line_h: int,
    rng: random.Random,
    *,
    line_index: int = 0,
    line_count: int = 1,
) -> Tuple[int, int, int, int]:
    """
    Generate a readable equation bbox inside a block.

    Multiple equation lines are placed into vertical slots to avoid overlap.
    """
    line_count = max(1, int(line_count))
    line_index = max(0, min(int(line_index), line_count - 1))

    xpad = max(8, int(0.03 * bw))
    usable_w = max(24, bw - 2 * xpad)

    if line_count <= 2:
        width_ratio = rng.uniform(0.72, 0.98)
    else:
        width_ratio = rng.uniform(0.58, 0.94)

    line_w = int(usable_w * width_ratio)
    line_w = max(32, min(line_w, usable_w))

    slot_y0 = by + int((bh * line_index) / line_count)
    slot_y1 = by + int((bh * (line_index + 1)) / line_count)
    slot_h = max(18, slot_y1 - slot_y0)

    actual_line_h = int(min(slot_h * rng.uniform(0.68, 0.92), line_h * 1.75))
    actual_line_h = max(20, min(actual_line_h, slot_h, bh))

    free_x = max(0, bw - line_w - 2 * xpad)
    free_y = max(0, slot_h - actual_line_h)

    x = bx + xpad + (int(rng.uniform(0.0, free_x)) if free_x > 0 else 0)
    y = slot_y0 + (
        int(rng.uniform(0.05, 0.95) * free_y)
        if free_y > 0
        else 0
    )

    return int(x), int(y), int(line_w), int(actual_line_h)



