# src/docsynthfab/layout/table_shapes.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from .common import choice_dist


def table_shape_for_block(
    bw: int,
    bh: int,
    density_level: str,
    page_family: str,
    rng: random.Random,
    *,
    table_diversity_scale: float = 0.75,
    table_empty_cell_scale: float = 0.0,
    table_merge_cell_scale: float = 0.25,
    table_shape_cfg: Dict[str, Any] | None = None,
) -> Tuple[int, int, Dict[str, object]]:
    """
    Generate a diverse table shape and style profile.

    YAML-connected controls:
    - table_diversity_scale: affects table family/style diversity.
    - table_empty_cell_scale: scales empty-cell probability.
    - table_merge_cell_scale: scales merged-cell-like behavior.
    """
    table_diversity_scale = max(0.0, min(float(table_diversity_scale), 2.0))
    table_empty_cell_scale = max(0.0, min(float(table_empty_cell_scale), 2.0))
    table_merge_cell_scale = max(0.0, min(float(table_merge_cell_scale), 2.0))


    def gaussian_int(
        low: int,
        high: int,
        mean_ratio: float = 0.55,
        std_ratio: float = 0.20,
    ) -> int:
        low = int(low)
        high = int(high)

        if high < low:
            low, high = high, low

        if high <= low:
            return low

        mean = low + (high - low) * mean_ratio
        std = max(0.35, (high - low) * std_ratio)

        for _ in range(8):
            value = int(round(rng.gauss(mean, std)))
            if low <= value <= high:
                return value

        return max(low, min(high, int(round(mean))))



    table_profiles: Dict[str, List[Dict[str, object]]] = {
        "worksheet": [
            {"kind": "worksheet_grid", "cols": (2, 5), "rows": (5, 12), "w": 0.24},
            {"kind": "answer_sheet", "cols": (3, 6), "rows": (6, 14), "w": 0.18},
            {"kind": "form_table", "cols": (2, 4), "rows": (4, 9), "w": 0.18},
            {"kind": "rubric_table", "cols": (4, 7), "rows": (4, 8), "w": 0.16},
            {"kind": "worksheet_grid", "cols": (4, 8), "rows": (5, 12), "w": 0.10},
        ],
        "academic": [
            {"kind": "scientific_result", "cols": (4, 8), "rows": (4, 9), "w": 0.25},
            {"kind": "stat_table", "cols": (3, 7), "rows": (4, 10), "w": 0.20},
            {"kind": "confusion_matrix", "cols": (3, 6), "rows": (3, 6), "w": 0.15},
            {"kind": "ablation_table", "cols": (4, 9), "rows": (3, 7), "w": 0.17},
            {"kind": "booktabs_table", "cols": (3, 6), "rows": (4, 8), "w": 0.23},
        ],
        "report": [
            {"kind": "invoice", "cols": (4, 8), "rows": (5, 14), "w": 0.22},
            {"kind": "financial_statement", "cols": (3, 7), "rows": (6, 16), "w": 0.20},
            {"kind": "kpi_dashboard_table", "cols": (3, 6), "rows": (3, 8), "w": 0.14},
            {"kind": "schedule", "cols": (4, 9), "rows": (5, 12), "w": 0.15},
            {"kind": "summary_table", "cols": (2, 5), "rows": (3, 8), "w": 0.17},
            {"kind": "ledger", "cols": (4, 8), "rows": (8, 18), "w": 0.12},
        ],
        "book": [
            {"kind": "comparison_table", "cols": (3, 6), "rows": (4, 9), "w": 0.25},
            {"kind": "reference_table", "cols": (2, 5), "rows": (5, 12), "w": 0.24},
            {"kind": "small_book_table", "cols": (2, 4), "rows": (3, 7), "w": 0.22},
            {"kind": "timeline_table", "cols": (3, 5), "rows": (4, 10), "w": 0.16},
            {"kind": "glossary_table", "cols": (2, 3), "rows": (5, 12), "w": 0.13},
        ],
        "notes": [
            {"kind": "quick_grid", "cols": (2, 5), "rows": (3, 8), "w": 0.25},
            {"kind": "handmade_list_table", "cols": (2, 4), "rows": (4, 10), "w": 0.25},
            {"kind": "borderless_notes_table", "cols": (2, 5), "rows": (3, 8), "w": 0.25},
            {"kind": "key_value_table", "cols": (2, 3), "rows": (4, 10), "w": 0.25},
        ],
    }

    profiles = table_profiles.get(page_family, table_profiles["report"])

    if table_diversity_scale <= 0.05:
        profile = profiles[0]
    else:
        weights = []

        for item in profiles:
            base_w = float(item.get("w", 1.0))

            if table_diversity_scale < 1.0:
                adjusted = base_w ** (1.0 / max(0.10, table_diversity_scale))
            else:
                adjusted = base_w ** (1.0 / table_diversity_scale)

            weights.append(max(0.0001, adjusted))

        total_w = sum(weights)
        pick = rng.random() * total_w
        acc = 0.0
        profile = profiles[-1]

        for item, weight in zip(profiles, weights):
            acc += weight

            if pick <= acc:
                profile = item
                break

    col_range = profile.get("cols", (3, 5))
    row_range = profile.get("rows", (4, 8))

    cols = gaussian_int(int(col_range[0]), int(col_range[1]))
    rows = gaussian_int(int(row_range[0]), int(row_range[1]))


    if density_level == "dense":
        rows += rng.randint(1, 4)

        if rng.random() < 0.55:
            cols += rng.randint(1, 2)

    elif density_level == "sparse":
        rows = max(2, rows - rng.randint(1, 3))

        if rng.random() < 0.40:
            cols = max(2, cols - 1)

    elif density_level == "mixed":
        if rng.random() < 0.55:
            rows += rng.randint(1, 3)

        if rng.random() < 0.35:
            cols += 1

    aspect = bw / max(1, bh)

    if aspect > 1.75:
        cols = max(cols, rng.randint(5, 10))
        rows = max(2, min(rows, rng.randint(3, 8)))
        table_variant = "wide"

    elif aspect < 0.80:
        rows = max(rows, rng.randint(7, 18))
        cols = max(2, min(cols, rng.randint(2, 5)))
        table_variant = "tall"

    else:
        if table_diversity_scale <= 0.05:
            table_variant = "balanced"
        else:
            table_variant = rng.choice(["balanced", "compact", "open"])

    shape_cfg = table_shape_cfg or {}

    try:
        min_rows = int(shape_cfg.get("min_rows", 2))
        max_rows = int(shape_cfg.get("max_rows", 24))
        min_cols = int(shape_cfg.get("min_cols", 2))
        max_cols = int(shape_cfg.get("max_cols", 12))
    except Exception:
        min_rows, max_rows = 2, 24
        min_cols, max_cols = 2, 12

    min_rows = max(1, min_rows)
    max_rows = max(1, max_rows)
    min_cols = max(1, min_cols)
    max_cols = max(1, max_cols)

    if max_rows < min_rows:
        min_rows, max_rows = max_rows, min_rows

    if max_cols < min_cols:
        min_cols, max_cols = max_cols, min_cols

    # Hard safety caps. GUI can request large tables, but extreme values
    # should not create impossible rendering workloads.
    min_rows = min(min_rows, 500)
    max_rows = min(max_rows, 500)
    min_cols = min(min_cols, 120)
    max_cols = min(max_cols, 120)

    if max_rows < min_rows:
        min_rows, max_rows = max_rows, min_rows

    if max_cols < min_cols:
        min_cols, max_cols = max_cols, min_cols

    rows = max(min_rows, min(rows, max_rows))
    cols = max(min_cols, min(cols, max_cols))


    kind = str(profile.get("kind", "summary_table"))

    if kind == "blank_grid":
        kind = "worksheet_grid"

    if kind in {"booktabs_table", "scientific_result", "ablation_table"}:
        border_dist = {
            "booktabs": 0.38,
            "header_rule": 0.24,
            "rows_only": 0.18,
            "borderless": 0.12,
            "full_grid": 0.08,
        }

    elif kind in {"invoice", "financial_statement", "ledger"}:
        border_dist = {
            "ledger": 0.34,
            "rows_only": 0.22,
            "full_grid": 0.18,
            "header_rule": 0.14,
            "outer_only": 0.08,
            "borderless": 0.04,
        }

    elif kind in {"form_table", "answer_sheet", "blank_grid", "worksheet_grid"}:
        border_dist = {
            "full_grid": 0.46,
            "outer_only": 0.14,
            "rows_only": 0.14,
            "cols_only": 0.08,
            "ledger": 0.08,
            "borderless": 0.10,
        }

    elif kind in {"quick_grid", "handmade_list_table", "borderless_notes_table", "key_value_table"}:
        border_dist = {
            "borderless": 0.36,
            "rows_only": 0.22,
            "outer_only": 0.14,
            "header_rule": 0.12,
            "full_grid": 0.10,
            "ledger": 0.06,
        }

    else:
        border_dist = {
            "full_grid": 0.24,
            "rows_only": 0.20,
            "cols_only": 0.08,
            "outer_only": 0.10,
            "header_rule": 0.16,
            "ledger": 0.10,
            "borderless": 0.12,
        }

    if table_diversity_scale <= 0.05:
        border_mode = "full_grid"
    else:
        border_mode = choice_dist(rng, border_dist, default="full_grid")

    if kind in {
        "invoice",
        "scientific_result",
        "stat_table",
        "financial_statement",
        "schedule",
        "booktabs_table",
        "ablation_table",
    }:
        header_rows = 1 if rng.random() < 0.94 else 2

    elif kind in {"form_table", "key_value_table"}:
        header_rows = 0 if rng.random() < 0.65 else 1

    else:
        header_rows = 1 if rng.random() < 0.75 else 0

    if kind in {
        "comparison_table",
        "confusion_matrix",
        "reference_table",
        "key_value_table",
    }:
        header_cols = 1 if rng.random() < 0.70 else 0

    else:
        header_cols = 1 if rng.random() < 0.28 else 0

    compact = bool(
        table_variant == "compact"
        or density_level == "dense"
        or rng.random() < 0.35
    )

    if table_diversity_scale <= 0.05:
        col_width_mode = "uniform"
        row_height_mode = "uniform"
    else:
        col_width_mode = rng.choice(
            ["uniform", "first_wide", "last_narrow", "ragged", "numeric"]
        )

        if kind in {"invoice", "financial_statement", "ledger"}:
            col_width_mode = rng.choice(["first_wide", "numeric", "ragged"])

        elif kind in {"confusion_matrix", "blank_grid", "worksheet_grid"}:
            col_width_mode = "uniform"

        elif kind in {"key_value_table", "form_table"}:
            col_width_mode = rng.choice(["first_wide", "ragged"])

        row_height_mode = rng.choice(["uniform", "header_tall", "ragged", "compact"])

        if header_rows > 0 and rng.random() < 0.70:
            row_height_mode = "header_tall"

        if density_level == "dense" and rng.random() < 0.50:
            row_height_mode = "compact"

    if kind in {"blank_grid", "form_table"}:
        base_empty_prob = rng.uniform(0.18, 0.48)

    elif kind in {"borderless_notes_table", "quick_grid", "summary_table"}:
        base_empty_prob = rng.uniform(0.08, 0.24)

    elif kind in {"invoice", "financial_statement", "ledger"}:
        base_empty_prob = rng.uniform(0.02, 0.14)

    else:
        base_empty_prob = rng.uniform(0.03, 0.18)

    empty_cell_prob = max(0.0, min(0.12, base_empty_prob * table_empty_cell_scale))
    merged_cells = bool(rng.random() < (0.32 * table_merge_cell_scale))

    if kind in {"confusion_matrix", "blank_grid"}:
        merged_cells = False

    if rows < 4 or cols < 3:
        merged_cells = False

    style: Dict[str, object] = {
        "table_kind": kind,
        "table_variant": table_variant,
        "header_rows": int(min(header_rows, rows - 1)),
        "header_cols": int(min(header_cols, cols - 1)),
        "compact": compact,
        "border_mode": border_mode,
        "zebra_rows": bool(
            rng.random()
            < (0.42 if kind in {"ledger", "financial_statement", "invoice"} else 0.24)
        ),
        "light_rules": bool(rng.random() < 0.58),
        "col_width_mode": col_width_mode,
        "row_height_mode": row_height_mode,
        "empty_cell_prob": float(empty_cell_prob),
        "merged_cells": bool(merged_cells),
        "cell_text_jitter": bool(
            rng.random() < (0.42 * max(0.10, table_diversity_scale))
        ),
        "table_diversity_scale": float(table_diversity_scale),
        "table_empty_cell_scale": float(table_empty_cell_scale),
        "table_merge_cell_scale": float(table_merge_cell_scale),
        "table_shape_cfg": {
            "min_rows": int(min_rows),
            "max_rows": int(max_rows),
            "min_cols": int(min_cols),
            "max_cols": int(max_cols),
        },
    }

    return cols, rows, style



