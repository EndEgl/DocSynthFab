from __future__ import annotations

from types import SimpleNamespace

from docsynthfab.render.geometry_utils import (
    _clamp_box,
    _collect_block_line_map,
    _intersects,
    _jump_past_obstacle,
    _line_kind_from_block,
    _pad_box,
    _try_relocate_line_bbox_down,
)


def test_clamp_box_keeps_xyxy_inside_page():
    assert _clamp_box(-10, -5, 120, 90, 100, 80) == (0, 0, 100, 80)
    assert _clamp_box(99, 79, 99, 79, 100, 80) == (99, 79, 100, 80)


def test_intersects_contract():
    assert _intersects((0, 0, 10, 10), (5, 5, 15, 15)) is True
    assert _intersects((0, 0, 10, 10), (10, 10, 20, 20)) is False
    assert _intersects((0, 0, 10, 10), (20, 20, 30, 30)) is False


def test_pad_box_clamps_to_page():
    assert _pad_box((5, 5, 15, 15), 10, 100, 100) == (0, 0, 25, 25)


def test_jump_past_obstacle_moves_to_after_intersecting_obstacle():
    y = _jump_past_obstacle(
        (0, 0, 20, 20),
        [(0, 0, 50, 30)],
        ycur=0,
        gap=5,
    )

    assert y == 35


def test_jump_past_obstacle_returns_same_y_when_no_hit():
    y = _jump_past_obstacle(
        (0, 0, 20, 20),
        [(30, 30, 50, 50)],
        ycur=0,
        gap=5,
    )

    assert y == 0


def test_try_relocate_line_bbox_down_finds_free_slot():
    ok, bbox = _try_relocate_line_bbox_down(
        0,
        0,
        20,
        10,
        [(0, 0, 100, 20)],
        w=100,
        h=100,
        y_max=100,
        tries=5,
        gap=5,
    )

    assert ok is True
    assert bbox[1] > 0
    assert bbox[2:] == (20, 10)


def test_try_relocate_line_bbox_down_returns_original_when_no_space():
    ok, bbox = _try_relocate_line_bbox_down(
        0,
        0,
        20,
        10,
        [(0, 0, 100, 90)],
        w=100,
        h=100,
        y_max=30,
        tries=3,
        gap=5,
    )

    assert ok is False
    assert bbox == (0, 0, 20, 10)


def test_line_kind_from_block_mapping():
    assert _line_kind_from_block("title") == "title"
    assert _line_kind_from_block("caption") == "caption"
    assert _line_kind_from_block("table") == "table_cell"
    assert _line_kind_from_block("list") == "list"
    assert _line_kind_from_block("paragraph") == "text"


def test_collect_block_line_map_sorts_by_line_order_then_global_order():
    page = SimpleNamespace(
        lines=[
            SimpleNamespace(block_id=1, line_order_in_block=2, global_line_order=2),
            SimpleNamespace(block_id=1, line_order_in_block=0, global_line_order=0),
            SimpleNamespace(block_id=2, line_order_in_block=0, global_line_order=1),
        ]
    )

    out = _collect_block_line_map(page)

    assert list(out) == [1, 2]
    assert [ln.line_order_in_block for ln in out[1]] == [0, 2]
    assert out[2][0].global_line_order == 1