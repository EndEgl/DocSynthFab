from __future__ import annotations

import random

from docsynthfab.layout.block_placement import (
    _apply_natural_text_block_x_jitter,
    assign_block_positions,
    block_height_ratio,
    resolve_columns,
)


def _assert_inside_page(item, w: int, h: int) -> None:
    _col, x, y, bw, bh, _kind, _style = item

    assert bw > 0
    assert bh > 0
    assert 0 <= x < w
    assert 0 <= y < h
    assert x + bw <= w
    assert y + bh <= h


def test_resolve_columns_contract():
    rng = random.Random(123)

    assert resolve_columns("single_col", "report", rng) == 1
    assert resolve_columns("double_col", "report", rng) == 2
    assert resolve_columns("mixed_cols", "academic", rng) == 2


def test_block_height_ratio_returns_positive_reasonable_value():
    rng = random.Random(123)

    for block_type in ["title", "paragraph", "list", "equation", "table", "figure"]:
        value = block_height_ratio(
            block_type,
            density_level="normal",
            page_family="report",
            rng=rng,
        )

        assert 0.0 < value < 1.0


def test_assign_block_positions_single_col_keeps_blocks_inside_page():
    w, h = 1200, 1600
    seq = ["title", "paragraph", "list", "table", "caption"]

    placed = assign_block_positions(
        seq=seq,
        layout_type="single_col",
        page_family="report",
        w=w,
        h=h,
        rng=random.Random(123),
        density_level="normal",
        page_size_name="a4_portrait",
    )

    assert len(placed) == len(seq)

    for item in placed:
        _assert_inside_page(item, w, h)

    title = placed[0]
    assert title[0] == -1
    assert title[5] == "title"
    assert title[6]["full_width"] is True


def test_assign_block_positions_double_col_uses_valid_column_ids():
    w, h = 1200, 1600
    seq = ["title", "paragraph", "paragraph", "table", "paragraph", "list"]

    placed = assign_block_positions(
        seq=seq,
        layout_type="double_col",
        page_family="academic",
        w=w,
        h=h,
        rng=random.Random(321),
        density_level="normal",
        page_size_name="a4_portrait",
    )

    assert len(placed) == len(seq)

    for item in placed:
        _assert_inside_page(item, w, h)
        assert item[0] in {-1, 0, 1}

    assert any(item[0] in {0, 1} for item in placed)


def test_caption_after_table_is_marked_as_caption_of_previous():
    w, h = 1200, 1600
    seq = ["table", "caption"]

    placed = assign_block_positions(
        seq=seq,
        layout_type="single_col",
        page_family="report",
        w=w,
        h=h,
        rng=random.Random(123),
        density_level="normal",
        page_size_name="a4_portrait",
    )

    table = placed[0]
    caption = placed[1]

    assert table[5] == "table"
    assert caption[5] == "caption"
    assert caption[6]["caption_of_prev"] is True
    assert caption[1] == table[1]
    assert caption[3] == table[3]


def test_apply_natural_text_block_x_jitter_marks_paragraph_style():
    style: dict[str, object] = {}

    new_x = _apply_natural_text_block_x_jitter(
        block_type="paragraph",
        x=100,
        bw=400,
        page_w=1200,
        rng=random.Random(123),
        style=style,
    )

    assert isinstance(new_x, int)
    assert "natural_x_jitter_px" in style
    assert new_x == 100 + int(style["natural_x_jitter_px"])


def test_apply_natural_text_block_x_jitter_does_not_touch_title():
    style: dict[str, object] = {}

    new_x = _apply_natural_text_block_x_jitter(
        block_type="title",
        x=100,
        bw=400,
        page_w=1200,
        rng=random.Random(123),
        style=style,
    )

    assert new_x == 100
    assert style == {}