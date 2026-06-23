# src/docsynthfab/layout/table_cell_bboxes.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple


def _table_cell_bboxes(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    rows: int,
    cols: int,
    *,
    compact: bool = False,
    header_rows: int = 0,
    header_cols: int = 0,
    style: Optional[Dict[str, object]] = None,
) -> List[Tuple[int, int, int, int]]:
    """
    Generate realistic table-cell text bboxes.

    Supports:
    - variable column widths,
    - variable row heights,
    - empty cells,
    - simple merged-cell-like behavior,
    - header row/header column padding differences.
    """
    style = style or {}

    rows = max(1, int(rows))
    cols = max(1, int(cols))
    bw = max(1, int(bw))
    bh = max(1, int(bh))

    seed = (
        int(bx) * 73_856_093
        ^ int(by) * 19_349_663
        ^ int(bw) * 83_492_791
        ^ int(bh) * 2_654_435_761
        ^ rows * 97_531
        ^ cols * 314_159
    ) & 0xFFFFFFFF

    local_rng = random.Random(seed)

    col_mode = str(style.get("col_width_mode", "uniform"))
    row_mode = str(style.get("row_height_mode", "uniform"))
    empty_prob = float(style.get("empty_cell_prob", 0.0))
    merged_cells = bool(style.get("merged_cells", False))
    cell_text_jitter = bool(style.get("cell_text_jitter", False))

    def make_weights(n: int, mode: str, axis: str) -> List[float]:
        if n <= 1:
            return [1.0]

        if mode == "uniform":
            weights = [1.0 for _ in range(n)]

        elif mode == "first_wide" and axis == "x":
            weights = [1.65] + [
                local_rng.uniform(0.75, 1.10)
                for _ in range(n - 1)
            ]

        elif mode == "last_narrow" and axis == "x":
            weights = [
                local_rng.uniform(0.95, 1.25)
                for _ in range(n - 1)
            ] + [0.65]

        elif mode == "numeric" and axis == "x":
            if n >= 4:
                weights = [1.65] + [
                    local_rng.uniform(0.70, 0.95)
                    for _ in range(n - 2)
                ] + [1.10]
            else:
                weights = [1.25] + [0.85 for _ in range(n - 1)]

        elif mode == "header_tall" and axis == "y":
            weights = [1.35] + [
                local_rng.uniform(0.85, 1.05)
                for _ in range(n - 1)
            ]

        elif mode == "compact" and axis == "y":
            weights = [0.95 for _ in range(n)]

        elif mode == "ragged":
            weights = [local_rng.uniform(0.65, 1.45) for _ in range(n)]

        else:
            weights = [local_rng.uniform(0.85, 1.15) for _ in range(n)]

        total = sum(weights) or 1.0
        return [weight / total for weight in weights]

    col_weights = make_weights(cols, col_mode, "x")
    row_weights = make_weights(rows, row_mode, "y")

    col_edges = [bx]
    acc_x = bx

    for col_idx, weight in enumerate(col_weights):
        if col_idx == cols - 1:
            acc_x = bx + bw
        else:
            acc_x += int(round(bw * weight))

        col_edges.append(acc_x)

    row_edges = [by]
    acc_y = by

    for row_idx, weight in enumerate(row_weights):
        if row_idx == rows - 1:
            acc_y = by + bh
        else:
            acc_y += int(round(bh * weight))

        row_edges.append(acc_y)

    cells: List[Tuple[int, int, int, int]] = []
    skip: set[Tuple[int, int]] = set()
    merge_map: Dict[Tuple[int, int], Tuple[int, int]] = {}

    if merged_cells:
        merge_count = local_rng.randint(1, max(1, min(4, (rows * cols) // 10)))

        for _ in range(merge_count):
            row_idx = local_rng.randint(max(0, header_rows), rows - 2)
            col_idx = local_rng.randint(max(0, header_cols), cols - 2)

            if (row_idx, col_idx) in skip:
                continue

            if local_rng.random() < 0.60:
                row_span, col_span = 1, 2
            else:
                row_span, col_span = 2, 1

            if row_idx + row_span > rows or col_idx + col_span > cols:
                continue

            merge_map[(row_idx, col_idx)] = (row_span, col_span)

            for rr in range(row_idx, row_idx + row_span):
                for cc in range(col_idx, col_idx + col_span):
                    if (rr, cc) != (row_idx, col_idx):
                        skip.add((rr, cc))

    for row_idx in range(rows):
        for col_idx in range(cols):
            if (row_idx, col_idx) in skip:
                continue

            is_header = row_idx < header_rows or col_idx < header_cols

            if not is_header and empty_prob > 0 and local_rng.random() < empty_prob:
                continue

            row_span, col_span = merge_map.get((row_idx, col_idx), (1, 1))

            x0 = col_edges[col_idx]
            y0 = row_edges[row_idx]
            x1 = col_edges[min(cols, col_idx + col_span)]
            y1 = row_edges[min(rows, row_idx + row_span)]

            cell_w = max(8, x1 - x0)
            cell_h = max(8, y1 - y0)

            if compact:
                pad_x = max(2, int(cell_w * 0.055))
                pad_y = max(2, int(cell_h * 0.085))
            else:
                pad_x = max(3, int(cell_w * 0.095))
                pad_y = max(3, int(cell_h * 0.155))

            if is_header:
                pad_x = max(2, int(pad_x * 0.75))
                pad_y = max(2, int(pad_y * 0.75))

            if cell_text_jitter and not is_header:
                pad_x += local_rng.randint(0, max(1, int(cell_w * 0.04)))
                pad_y += local_rng.randint(0, max(1, int(cell_h * 0.05)))

            x = x0 + pad_x
            y = y0 + pad_y
            ww = max(6, cell_w - 2 * pad_x)
            hh = max(6, cell_h - 2 * pad_y)

            cells.append((int(x), int(y), int(ww), int(hh)))

    return cells



