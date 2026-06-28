# src/docsynthfab/layout/block_placement.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from .common import clamp


PlacedBlock = Tuple[int, int, int, int, int, str, Dict[str, object]]

def _apply_natural_text_block_x_jitter(
    *,
    block_type: str,
    x: int,
    bw: int,
    page_w: int,
    rng: random.Random,
    style: Dict[str, object],
) -> int:
    """
    Add small safe horizontal variation to text blocks so paragraphs do not look
    perfectly grid-aligned. This is block-level only; it does not disturb line
    baselines and is safer while line-overlap checks still fail.
    """
    if block_type not in {"paragraph", "list"}:
        return x

    max_shift = min(18, max(4, int(page_w * 0.006)))
    shift = int(round(rng.uniform(-max_shift, max_shift)))

    left_limit = int(page_w * 0.055)
    right_limit = max(left_limit, page_w - int(page_w * 0.055) - bw)

    new_x = clamp(x + shift, left_limit, right_limit)
    style["natural_x_jitter_px"] = int(new_x - x)

    return new_x


def resolve_columns(
    layout_type: str,
    page_family: str,
    rng: random.Random,
) -> int:
    """Resolve the number of layout columns for a page."""
    if layout_type == "single_col":
        return 1

    if layout_type == "double_col":
        return 2

    if page_family == "academic":
        return 2

    return 2 if rng.random() < 0.70 else 1


def block_height_ratio(
    block_type: str,
    density_level: str,
    page_family: str,
    rng: random.Random,
) -> float:
    """Sample a height ratio for a block type under a page density/family."""
    base = {
        "title": (0.030, 0.050),
        "paragraph": (0.180, 0.400),
        "list": (0.120, 0.250),
        "equation": (0.105, 0.220),
        "table": (0.140, 0.280),
        "figure": (0.220, 0.450),
        "caption": (0.020, 0.035),
        "header": (0.015, 0.030),
        "footer": (0.015, 0.030),
    }.get(block_type, (0.120, 0.280))

    lo, hi = base

    if density_level == "dense":
        lo *= 1.20
        hi *= 1.45

    elif density_level == "sparse":
        lo *= 0.86
        hi *= 0.95

    elif density_level == "mixed":
        if rng.random() < 0.50:
            lo *= 0.72
            hi *= 0.92
        else:
            lo *= 1.08
            hi *= 1.28

    if page_family == "notes":
        if block_type in {"list", "paragraph"}:
            lo *= 0.92
            hi *= 1.08

    elif page_family == "worksheet":
        if block_type in {"list", "table"}:
            lo *= 1.12
            hi *= 1.22

    elif page_family == "academic":
        if block_type in {"equation", "figure"}:
            lo *= 1.18
            hi *= 1.36

        if block_type == "paragraph":
            lo *= 1.08
            hi *= 1.14

    return rng.uniform(lo, hi)


def assign_block_positions(
    seq: List[str],
    layout_type: str,
    page_family: str,
    w: int,
    h: int,
    rng: random.Random,
    density_level: str,
    page_size_name: str,
) -> List[PlacedBlock]:
    """Return tuples in the form: (column_id, x, y, bw, bh, block_type, style)."""
    ncol = resolve_columns(layout_type, page_family, rng)

    margin_x = int(0.08 * w)
    margin_y = int(0.08 * h)
    usable_w = w - 2 * margin_x
    usable_h = h - 2 * margin_y

    gutter = int(0.03 * w) if ncol == 2 else 0
    col_w = (usable_w - gutter) // ncol if ncol == 2 else usable_w

    col_xs = [margin_x] if ncol == 1 else [margin_x, margin_x + col_w + gutter]
    col_y = [margin_y for _ in range(ncol)]

    placed: List[PlacedBlock] = []

    mixed_fullwidth_budget = 0

    if layout_type == "mixed_cols":
        mixed_fullwidth_budget = 2 if seq and seq[0] == "title" else 1

    current_col = 0
    prev_item: Optional[PlacedBlock] = None
    bottom_limit = h - margin_y

    for index, block_type in enumerate(seq):
        bh = int(block_height_ratio(block_type, density_level, page_family, rng) * h)
        bh = clamp(bh, 24, max(40, int(usable_h * 0.82)))

        style: Dict[str, object] = {
            "page_family": page_family,
            "layout_type": layout_type,
            "page_size_name": page_size_name,
            "orientation": "landscape" if w > h else "portrait",
        }

        if block_type == "caption" and prev_item is not None and prev_item[5] in {"figure", "table"}:
            prev_col, prev_x, prev_y, prev_bw, prev_bh, _, _ = prev_item
            cap_h = max(22, int(bh * 0.65))
            cap_gap = int(rng.uniform(0.003, 0.007) * h)

            x = prev_x
            y = prev_y + prev_bh + cap_gap
            bw = prev_bw
            bh = cap_h

            if y + bh > bottom_limit:
                bh = max(16, bottom_limit - y)

            if prev_col == -1:
                for col_idx in range(ncol):
                    col_y[col_idx] = max(col_y[col_idx], y + bh + cap_gap)

                column_id = -1
                style["full_width"] = True

            else:
                col_y[prev_col] = max(col_y[prev_col], y + bh + cap_gap)
                column_id = prev_col

            style["caption_of_prev"] = True

            placed_item = (column_id, x, y, bw, bh, block_type, style)
            placed.append(placed_item)
            prev_item = placed_item
            continue

        full_width = False

        if block_type == "title":
            full_width = True

        elif layout_type == "mixed_cols" and index < mixed_fullwidth_budget:
            full_width = True

        elif block_type == "table" and ncol == 2 and rng.random() < 0.45:
            full_width = True

        elif (
            block_type == "figure"
            and page_family in {"report", "book"}
            and ncol == 2
            and rng.random() < 0.22
        ):
            full_width = True

        if full_width:
            x = margin_x
            y = max(col_y)
            bw = usable_w

            if block_type == "title":
                gap = int(rng.uniform(0.015, 0.030) * h)
            else:
                gap = int(rng.uniform(0.005, 0.012) * h)

            if y + bh > bottom_limit:
                bh = max(24, bottom_limit - y)

            for col_idx in range(ncol):
                col_y[col_idx] = y + bh + gap

            column_id = -1
            style["full_width"] = True

            placed_item = (column_id, x, y, bw, bh, block_type, style)
            placed.append(placed_item)
            prev_item = placed_item
            continue

        if ncol == 1:
            current_col = 0

        else:
            if layout_type == "double_col":
                if col_y[current_col] + bh > bottom_limit and current_col < ncol - 1:
                    current_col += 1

            else:
                current_col = 0 if col_y[0] <= col_y[1] else 1

        current_col = clamp(current_col, 0, ncol - 1)

        x = col_xs[current_col]
        y = col_y[current_col]
        bw = col_w

        if y + bh > bottom_limit and ncol == 2:
            other_col = 1 - current_col

            if col_y[other_col] + bh <= bottom_limit:
                current_col = other_col
                x = col_xs[current_col]
                y = col_y[current_col]

        if y + bh > bottom_limit:
            bh = max(24, bottom_limit - y)

        gap = int(rng.uniform(0.005, 0.012) * h)
        col_y[current_col] = y + bh + gap

        x = _apply_natural_text_block_x_jitter(
            block_type=block_type,
            x=x,
            bw=bw,
            page_w=w,
            rng=rng,
            style=style,
        )

        column_id = current_col
        placed_item = (column_id, x, y, bw, bh, block_type, style)
        
        placed.append(placed_item)
        prev_item = placed_item

    return placed



