# src/docsynthfab/render/table_renderer.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from PIL import ImageDraw


def _draw_table_structure(
    draw: ImageDraw.ImageDraw,
    bx0: int,
    by0: int,
    bx1: int,
    by1: int,
    *,
    rows: int,
    cols: int,
    style: Dict[str, Any],
    rng: random.Random,
) -> None:
    rows = max(1, int(rows))
    cols = max(1, int(cols))

    bw = max(1, bx1 - bx0)
    bh = max(1, by1 - by0)

    header_rows = max(0, int(style.get("header_rows", 0)))
    header_cols = max(0, int(style.get("header_cols", 0)))
    header_rows = min(header_rows, max(0, rows - 1))
    header_cols = min(header_cols, max(0, cols - 1))

    border_mode = str(style.get("border_mode", "full_grid"))
    zebra_rows = bool(style.get("zebra_rows", False))
    light_rules = bool(style.get("light_rules", False))
    table_kind = str(style.get("table_kind", "generic"))
    col_mode = str(style.get("col_width_mode", "uniform"))
    row_mode = str(style.get("row_height_mode", "uniform"))
    merged_cells = bool(style.get("merged_cells", False))

    rule_dark = 70 if not light_rules else 115
    rule_mid = 100 if not light_rules else 150
    rule_light = 185 if not light_rules else 210

    outer_col = (rule_dark, rule_dark, rule_dark)
    major_col = (rule_mid, rule_mid, rule_mid)
    minor_col = (rule_light, rule_light, rule_light)

    seed = (
        int(bx0) * 73856093
        ^ int(by0) * 19349663
        ^ int(bw) * 83492791
        ^ int(bh) * 2654435761
        ^ rows * 97531
        ^ cols * 314159
    ) & 0xFFFFFFFF

    local_rng = random.Random(seed)

    def make_weights(n: int, mode: str, axis: str) -> List[float]:
        if n <= 1:
            return [1.0]

        if mode == "uniform":
            weights = [1.0 for _ in range(n)]

        elif mode == "first_wide" and axis == "x":
            weights = [1.65] + [local_rng.uniform(0.75, 1.10) for _ in range(n - 1)]

        elif mode == "last_narrow" and axis == "x":
            weights = [local_rng.uniform(0.95, 1.25) for _ in range(n - 1)] + [0.65]

        elif mode == "numeric" and axis == "x":
            if n >= 4:
                weights = [1.65] + [local_rng.uniform(0.70, 0.95) for _ in range(n - 2)] + [1.10]
            else:
                weights = [1.25] + [0.85 for _ in range(n - 1)]

        elif mode == "header_tall" and axis == "y":
            weights = [1.35] + [local_rng.uniform(0.85, 1.05) for _ in range(n - 1)]

        elif mode == "compact" and axis == "y":
            weights = [0.95 for _ in range(n)]

        elif mode == "ragged":
            weights = [local_rng.uniform(0.65, 1.45) for _ in range(n)]

        else:
            weights = [local_rng.uniform(0.85, 1.15) for _ in range(n)]

        total = sum(weights) or 1.0
        return [w / total for w in weights]

    col_weights = make_weights(cols, col_mode, "x")
    row_weights = make_weights(rows, row_mode, "y")

    col_edges = [bx0]
    acc_x = bx0

    for i, wt in enumerate(col_weights):
        if i == cols - 1:
            acc_x = bx1
        else:
            acc_x += int(round(bw * wt))
        col_edges.append(acc_x)

    row_edges = [by0]
    acc_y = by0

    for i, wt in enumerate(row_weights):
        if i == rows - 1:
            acc_y = by1
        else:
            acc_y += int(round(bh * wt))
        row_edges.append(acc_y)

    if table_kind in {"invoice", "financial_statement", "ledger"}:
        if local_rng.random() < 0.45:
            draw.rectangle((bx0, by0, bx1, by1), fill=(252, 252, 252))

    elif table_kind in {"booktabs_table", "scientific_result", "ablation_table"}:
        if local_rng.random() < 0.25:
            draw.rectangle((bx0, by0, bx1, by1), fill=(253, 253, 253))

    elif table_kind in {"form_table", "answer_sheet", "worksheet_grid", "blank_grid"}:
        if local_rng.random() < 0.30:
            draw.rectangle((bx0, by0, bx1, by1), fill=(255, 255, 255))

    if header_rows > 0:
        for r in range(min(header_rows, rows)):
            y0 = row_edges[r]
            y1 = row_edges[r + 1]

            if table_kind in {"invoice", "financial_statement", "ledger"}:
                fill = (238, 238, 238)
            elif table_kind in {"booktabs_table", "scientific_result", "ablation_table"}:
                fill = (246, 246, 246)
            elif table_kind in {"notes", "quick_grid", "handmade_list_table", "borderless_notes_table"}:
                fill = (250, 250, 250)
            else:
                fill = (242, 242, 242)

            draw.rectangle((bx0, y0, bx1, y1), fill=fill)

    if header_cols > 0:
        for c in range(min(header_cols, cols)):
            x0 = col_edges[c]
            x1 = col_edges[c + 1]

            if table_kind in {"confusion_matrix", "comparison_table", "reference_table"}:
                fill = (240, 240, 240)
            else:
                fill = (246, 246, 246)

            draw.rectangle((x0, by0, x1, by1), fill=fill)

    if zebra_rows and rows >= 3:
        start_r = max(1, header_rows)

        for r in range(start_r, rows):
            if (r - start_r) % 2 == 1:
                y0 = row_edges[r]
                y1 = row_edges[r + 1]

                if table_kind in {"ledger", "financial_statement", "invoice"}:
                    fill = (248, 248, 248)
                else:
                    fill = (250, 250, 250)

                draw.rectangle((bx0, y0, bx1, y1), fill=fill)

    skip_v_segments: set[Tuple[int, int]] = set()
    skip_h_segments: set[Tuple[int, int]] = set()

    if merged_cells and rows >= 4 and cols >= 3:
        merge_count = local_rng.randint(1, max(1, min(4, (rows * cols) // 10)))

        for _ in range(merge_count):
            r = local_rng.randint(max(0, header_rows), rows - 2)
            c = local_rng.randint(max(0, header_cols), cols - 2)

            if local_rng.random() < 0.60:
                skip_v_segments.add((c + 1, r))
            else:
                skip_h_segments.add((r + 1, c))

    def draw_outer() -> None:
        draw.rectangle((bx0, by0, bx1, by1), outline=outer_col, width=2)

    def draw_horizontal_lines(include_outer: bool = False) -> None:
        start = 0 if include_outer else 1
        end = rows + 1 if include_outer else rows

        for r in range(start, end):
            y = row_edges[r]

            if r == 0 or r == rows:
                col = outer_col
                width = 2
            elif header_rows > 0 and r == header_rows:
                col = outer_col
                width = 2
            else:
                col = minor_col if border_mode in {"ledger", "rows_only", "booktabs"} else major_col
                width = 1

            if skip_h_segments:
                for c in range(cols):
                    if (r, c) in skip_h_segments:
                        continue
                    draw.line(
                        (col_edges[c], y, col_edges[c + 1], y),
                        fill=col,
                        width=width,
                    )
            else:
                draw.line((bx0, y, bx1, y), fill=col, width=width)

    def draw_vertical_lines(include_outer: bool = False) -> None:
        start = 0 if include_outer else 1
        end = cols + 1 if include_outer else cols

        for c in range(start, end):
            x = col_edges[c]

            if c == 0 or c == cols:
                col = outer_col
                width = 2
            elif header_cols > 0 and c == header_cols:
                col = outer_col
                width = 2
            else:
                col = minor_col if border_mode in {"cols_only"} else major_col
                width = 1

            if skip_v_segments:
                for r in range(rows):
                    if (c, r) in skip_v_segments:
                        continue
                    draw.line(
                        (x, row_edges[r], x, row_edges[r + 1]),
                        fill=col,
                        width=width,
                    )
            else:
                draw.line((x, by0, x, by1), fill=col, width=width)

    if border_mode == "borderless":
        if header_rows > 0:
            y = row_edges[min(header_rows, rows)]
            draw.line((bx0, y, bx1, y), fill=major_col, width=2)

        if table_kind in {"key_value_table", "form_table"} and local_rng.random() < 0.50:
            draw_horizontal_lines(include_outer=False)

        return

    if border_mode == "outer_only":
        draw_outer()
        return

    if border_mode == "header_rule":
        if header_rows > 0:
            y = row_edges[min(header_rows, rows)]
            draw.line((bx0, y, bx1, y), fill=outer_col, width=2)

        draw.line((bx0, by0, bx1, by0), fill=major_col, width=1)
        draw.line((bx0, by1, bx1, by1), fill=major_col, width=1)
        return

    if border_mode == "booktabs":
        draw.line((bx0, by0, bx1, by0), fill=outer_col, width=2)

        if header_rows > 0:
            y = row_edges[min(header_rows, rows)]
            draw.line((bx0, y, bx1, y), fill=outer_col, width=2)

        draw.line((bx0, by1, bx1, by1), fill=outer_col, width=2)
        return

    if border_mode == "rows_only":
        draw_horizontal_lines(include_outer=False)
        return

    if border_mode == "cols_only":
        draw_vertical_lines(include_outer=False)
        return

    if border_mode == "ledger":
        draw.line((bx0, by0, bx1, by0), fill=outer_col, width=2)

        if header_rows > 0:
            y = row_edges[min(header_rows, rows)]
            draw.line((bx0, y, bx1, y), fill=outer_col, width=2)

        for r in range(max(1, header_rows + 1), rows):
            y = row_edges[r]
            draw.line((bx0, y, bx1, y), fill=minor_col, width=1)

        draw.line((bx0, by1, bx1, by1), fill=major_col, width=1)

        if local_rng.random() < 0.35:
            draw_vertical_lines(include_outer=False)

        return

    draw_outer()
    draw_vertical_lines(include_outer=False)
    draw_horizontal_lines(include_outer=False)



