from __future__ import annotations

import random

from docsynthfab.layout.line_planning import _initial_line_plan
from docsynthfab.layout.line_rebalance import _rebalance_line_counts
from docsynthfab.layout.specs import BlockSpec


def _block(
    block_id: int,
    block_type: str,
    bbox=(0, 0, 400, 240),
) -> BlockSpec:
    return BlockSpec(
        block_id=block_id,
        block_type=block_type,
        block_order=block_id,
        column_id=0,
        bbox=bbox,
        style={},
    )


def test_initial_line_plan_handles_basic_block_types():
    blocks = [
        _block(0, "title", bbox=(0, 0, 400, 80)),
        _block(1, "paragraph", bbox=(0, 100, 400, 300)),
        _block(2, "list", bbox=(0, 420, 400, 240)),
        _block(3, "equation", bbox=(0, 680, 400, 160)),
        _block(4, "figure", bbox=(0, 860, 400, 300)),
        _block(5, "caption", bbox=(0, 1180, 400, 60)),
    ]

    mins, desired, caps = _initial_line_plan(
        blocks=blocks,
        base_lh=24,
        page_family="report",
        density_level="normal",
        rng=random.Random(123),
    )

    assert len(mins) == len(blocks)
    assert len(desired) == len(blocks)
    assert len(caps) == len(blocks)

    assert mins[0] == desired[0] == 1
    assert mins[4] == desired[4] == caps[4] == 0
    assert mins[5] == desired[5] == 1

    for mn, des, cap in zip(mins, desired, caps):
        assert 0 <= mn <= des <= cap


def test_initial_line_plan_table_writes_shape_into_block_style():
    table = _block(0, "table", bbox=(0, 0, 480, 480))

    mins, desired, caps = _initial_line_plan(
        blocks=[table],
        base_lh=24,
        page_family="worksheet",
        density_level="normal",
        rng=random.Random(456),
        table_empty_cell_scale=0.0,
        table_shape_cfg={
            "min_rows": 3,
            "max_rows": 6,
            "min_cols": 2,
            "max_cols": 4,
        },
    )

    assert len(mins) == 1
    assert len(desired) == 1
    assert len(caps) == 1

    assert 3 <= table.style["table_rows"] <= 6
    assert 2 <= table.style["table_cols"] <= 4
    assert table.style["table_kind"] != "blank_grid"
    assert table.style["empty_cell_prob"] == 0.0

    cells = int(table.style["table_rows"]) * int(table.style["table_cols"])
    assert 2 <= mins[0] <= desired[0] <= cells
    assert caps[0] >= desired[0]


def test_rebalance_line_counts_grows_toward_target_without_exceeding_caps():
    blocks = [
        _block(0, "paragraph", bbox=(0, 0, 400, 400)),
        _block(1, "list", bbox=(0, 420, 400, 300)),
        _block(2, "equation", bbox=(0, 740, 400, 160)),
    ]

    mins = [1, 1, 1]
    desired = [2, 2, 1]
    caps = [8, 6, 3]

    out = _rebalance_line_counts(
        blocks=blocks,
        mins=mins,
        desired=desired,
        caps=caps,
        target_total=12,
        rng=random.Random(123),
    )

    assert sum(out) == 12
    assert all(mn <= value <= cap for value, mn, cap in zip(out, mins, caps))


def test_rebalance_line_counts_shrinks_toward_target_without_going_below_mins():
    blocks = [
        _block(0, "paragraph", bbox=(0, 0, 400, 400)),
        _block(1, "list", bbox=(0, 420, 400, 300)),
        _block(2, "equation", bbox=(0, 740, 400, 160)),
    ]

    mins = [1, 1, 1]
    desired = [8, 6, 3]
    caps = [8, 6, 3]

    out = _rebalance_line_counts(
        blocks=blocks,
        mins=mins,
        desired=desired,
        caps=caps,
        target_total=6,
        rng=random.Random(123),
    )

    assert sum(out) == 6
    assert all(mn <= value <= cap for value, mn, cap in zip(out, mins, caps))