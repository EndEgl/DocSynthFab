from __future__ import annotations

import random

from docsynthfab.layout.table_shapes import table_shape_for_block


def test_table_shape_default_does_not_generate_blank_or_empty_tables():
    rng = random.Random(123)

    for page_family in ["worksheet", "academic", "report", "book", "notes"]:
        for density in ["sparse", "normal", "dense", "mixed"]:
            for _ in range(80):
                cols, rows, style = table_shape_for_block(
                    480,
                    480,
                    density,
                    page_family,
                    rng,
                    table_shape_cfg={
                        "min_rows": 2,
                        "max_rows": 24,
                        "min_cols": 2,
                        "max_cols": 12,
                    },
                )

                assert rows >= 2
                assert cols >= 2
                assert rows <= 24
                assert cols <= 12

                assert style["table_kind"] != "blank_grid"
                assert style["empty_cell_prob"] == 0.0
                assert style["table_empty_cell_scale"] == 0.0


def test_table_shape_empty_cell_probability_is_capped_when_enabled():
    rng = random.Random(456)

    for _ in range(250):
        cols, rows, style = table_shape_for_block(
            480,
            480,
            "normal",
            "worksheet",
            rng,
            table_empty_cell_scale=2.0,
            table_shape_cfg={
                "min_rows": 2,
                "max_rows": 24,
                "min_cols": 2,
                "max_cols": 12,
            },
        )

        assert rows >= 2
        assert cols >= 2
        assert style["table_kind"] != "blank_grid"
        assert 0.0 <= style["empty_cell_prob"] <= 0.12


def test_table_shape_respects_user_row_col_bounds():
    rng = random.Random(789)

    for _ in range(200):
        cols, rows, style = table_shape_for_block(
            480,
            480,
            "dense",
            "report",
            rng,
            table_shape_cfg={
                "min_rows": 6,
                "max_rows": 10,
                "min_cols": 3,
                "max_cols": 5,
            },
        )

        assert 6 <= rows <= 10
        assert 3 <= cols <= 5

        cfg = style["table_shape_cfg"]
        assert cfg["min_rows"] == 6
        assert cfg["max_rows"] == 10
        assert cfg["min_cols"] == 3
        assert cfg["max_cols"] == 5


def test_table_shape_sampling_stays_varied_and_inside_bounds():
    rng = random.Random(999)

    row_values = []
    col_values = []

    for _ in range(500):
        cols, rows, _style = table_shape_for_block(
            480,
            480,
            "normal",
            "report",
            rng,
            table_diversity_scale=0.0,
            table_shape_cfg={
                "min_rows": 5,
                "max_rows": 14,
                "min_cols": 4,
                "max_cols": 8,
            },
        )

        row_values.append(rows)
        col_values.append(cols)

    assert min(row_values) >= 5
    assert max(row_values) <= 14
    assert min(col_values) >= 4
    assert max(col_values) <= 8

    row_mean = sum(row_values) / len(row_values)
    col_mean = sum(col_values) / len(col_values)

    assert 7.0 <= row_mean <= 12.5
    assert 5.0 <= col_mean <= 7.5

    row_edge_ratio = sum(v in {5, 14} for v in row_values) / len(row_values)
    col_edge_ratio = sum(v in {4, 8} for v in col_values) / len(col_values)

    assert row_edge_ratio < 0.35
    assert col_edge_ratio < 0.45