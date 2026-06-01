# src/ai1_gen/layout/line_planning.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import List, Tuple

from .line_metrics import _max_lines_in_block
from .specs import BlockSpec
from .table_shapes import table_shape_for_block as _table_shape_for_block


def _initial_line_plan(
    blocks: List[BlockSpec],
    base_lh: int,
    page_family: str,
    density_level: str,
    rng: random.Random,
    *,
    table_diversity_scale: float = 0.75,
    table_empty_cell_scale: float = 0.35,
    table_merge_cell_scale: float = 0.25,
) -> Tuple[List[int], List[int], List[int]]:
    """Return minimum, desired, and capacity line counts per block."""
    mins: List[int] = []
    desired: List[int] = []
    caps: List[int] = []

    for block in blocks:
        block_type = block.block_type
        cap = _max_lines_in_block(block, base_lh)

        if block_type == "title":
            mn = des = 1
            cap = max(1, cap)

        elif block_type == "equation":
            cap = max(1, cap)

            if density_level == "dense":
                mn = min(cap, 2)
                hi = min(cap, 5)
                lo = min(hi, max(mn, 3))
                des = rng.randint(lo, hi) if hi >= lo else hi

            elif density_level == "normal":
                mn = 1
                hi = min(cap, 3)
                lo = min(hi, 2)
                des = rng.randint(lo, hi) if hi >= lo else hi

            elif density_level == "mixed":
                mn = 1
                hi = min(cap, 4)
                lo = min(hi, 2)
                des = rng.randint(lo, hi) if hi >= lo else hi

            else:
                mn = 1
                hi = min(cap, 2)
                des = rng.randint(1, hi) if hi >= 1 else 1

        elif block_type == "figure":
            mn = des = 0
            cap = 0

        elif block_type == "caption":
            mn = des = 1
            cap = max(1, min(cap, 2))

        elif block_type == "table":
            cols, rows, table_style = _table_shape_for_block(
                block.bbox[2],
                block.bbox[3],
                density_level,
                page_family,
                rng,
                table_diversity_scale=table_diversity_scale,
                table_empty_cell_scale=table_empty_cell_scale,
                table_merge_cell_scale=table_merge_cell_scale,
            )

            block.style["table_cols"] = cols
            block.style["table_rows"] = rows
            block.style.update(table_style)

            cells = cols * rows
            empty_prob = float(table_style.get("empty_cell_prob", 0.0))

            expected_visible_cells = int(round(cells * (1.0 - min(0.80, empty_prob))))
            expected_visible_cells = max(2, expected_visible_cells)

            if table_style.get("table_variant") == "wide":
                fill_ratio = rng.uniform(0.78, 0.96)

            elif table_style.get("table_variant") == "tall":
                fill_ratio = rng.uniform(0.82, 0.98)

            else:
                fill_ratio = rng.uniform(0.80, 1.00)

            desired_cells = max(2, int(round(expected_visible_cells * fill_ratio)))

            cap = max(desired_cells, cap)
            mn = max(2, min(cells, desired_cells))
            des = max(mn, min(cells, desired_cells))

        elif block_type == "list":
            mn = 2 if cap >= 2 else 1

            if density_level == "dense":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.68, 0.95)))))

            elif density_level == "sparse":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.45, 0.70)))))

            else:
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.55, 0.86)))))

        else:
            mn = 2 if cap >= 2 else 1

            if page_family == "notes":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.45, 0.72)))))

            elif page_family == "worksheet":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.40, 0.68)))))

            elif density_level == "dense":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.72, 0.98)))))

            elif density_level == "sparse":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.48, 0.74)))))

            else:
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.58, 0.90)))))

        mins.append(mn)
        desired.append(des)
        caps.append(cap)

    return mins, desired, caps