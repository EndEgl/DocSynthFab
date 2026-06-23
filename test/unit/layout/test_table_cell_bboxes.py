from __future__ import annotations

from docsynthfab.layout.table_cell_bboxes import _table_cell_bboxes


def _assert_cells_inside(cells, bx: int, by: int, bw: int, bh: int) -> None:
    for x, y, w, h in cells:
        assert w > 0
        assert h > 0
        assert bx <= x < bx + bw
        assert by <= y < by + bh
        assert x + w <= bx + bw
        assert y + h <= by + bh


def test_table_cell_bboxes_generates_one_bbox_per_cell_when_no_empty_or_merge():
    bx, by, bw, bh = 100, 200, 600, 300

    cells = _table_cell_bboxes(
        bx,
        by,
        bw,
        bh,
        rows=4,
        cols=5,
        compact=False,
        header_rows=0,
        header_cols=0,
        style={
            "empty_cell_prob": 0.0,
            "merged_cells": False,
            "cell_text_jitter": False,
            "col_width_mode": "uniform",
            "row_height_mode": "uniform",
        },
    )

    assert len(cells) == 20
    _assert_cells_inside(cells, bx, by, bw, bh)


def test_table_cell_bboxes_compact_cells_are_inside_table():
    bx, by, bw, bh = 20, 30, 400, 220

    cells = _table_cell_bboxes(
        bx,
        by,
        bw,
        bh,
        rows=3,
        cols=4,
        compact=True,
        header_rows=1,
        header_cols=1,
        style={
            "empty_cell_prob": 0.0,
            "merged_cells": False,
            "cell_text_jitter": True,
            "col_width_mode": "uniform",
            "row_height_mode": "header_tall",
        },
    )

    assert len(cells) == 12
    _assert_cells_inside(cells, bx, by, bw, bh)


def test_table_cell_bboxes_empty_prob_keeps_headers_but_skips_body_cells():
    bx, by, bw, bh = 100, 100, 500, 300

    cells = _table_cell_bboxes(
        bx,
        by,
        bw,
        bh,
        rows=4,
        cols=5,
        compact=False,
        header_rows=1,
        header_cols=0,
        style={
            "empty_cell_prob": 1.0,
            "merged_cells": False,
            "cell_text_jitter": False,
            "col_width_mode": "uniform",
            "row_height_mode": "uniform",
        },
    )

    assert len(cells) == 5
    _assert_cells_inside(cells, bx, by, bw, bh)


def test_table_cell_bboxes_merged_cells_do_not_exceed_full_cell_count():
    bx, by, bw, bh = 100, 100, 500, 300

    cells = _table_cell_bboxes(
        bx,
        by,
        bw,
        bh,
        rows=6,
        cols=6,
        compact=False,
        header_rows=1,
        header_cols=1,
        style={
            "empty_cell_prob": 0.0,
            "merged_cells": True,
            "cell_text_jitter": True,
            "col_width_mode": "ragged",
            "row_height_mode": "ragged",
        },
    )

    assert 1 <= len(cells) <= 36
    _assert_cells_inside(cells, bx, by, bw, bh)


def test_table_cell_bboxes_handles_small_table_bbox_safely():
    bx, by, bw, bh = 0, 0, 80, 60

    cells = _table_cell_bboxes(
        bx,
        by,
        bw,
        bh,
        rows=2,
        cols=2,
        compact=True,
        style={
            "empty_cell_prob": 0.0,
            "merged_cells": False,
            "cell_text_jitter": False,
        },
    )

    assert len(cells) == 4
    _assert_cells_inside(cells, bx, by, bw, bh)