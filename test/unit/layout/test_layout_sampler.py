from __future__ import annotations

import random
from typing import Any

from docsynthfab.layout import BlockSpec, LineSpec, PageSpec, sample_page_spec
from docsynthfab.layout.layout_sampler import (
    _box_too_close_or_overlapping,
    _clamp_block_xy,
    _overlap_ratio_min_area_xywh,
    _resolve_block_overlaps_after_occupancy,
    _target_counts,
)


class DummyCfg:
    def __init__(self, raw: dict[str, Any] | None = None):
        self.raw = raw or {}

    def density_dist(self):
        return {"normal": 1.0}

    def scale_dist(self):
        return {"dpi200": 1.0}

    def noise_dist(self):
        return {"clean": 1.0}

    def density_targets(self):
        return {
            "normal": {
                "line_count_range": (12, 18),
                "block_count_range": (4, 6),
            },
            "dense": {
                "line_count_range": (28, 36),
                "block_count_range": (7, 10),
            },
            "sparse": {
                "line_count_range": (6, 10),
                "block_count_range": (2, 4),
            },
            "mixed": {
                "line_count_range": (16, 24),
                "block_count_range": (4, 7),
            },
        }


def _cfg_text_only() -> DummyCfg:
    return DummyCfg(
        {
            "content": {
                "block_mix": {
                    "text": 100,
                    "table": 0,
                    "latex": 0,
                },
                "hard_negative_page_prob": 0.0,
            },
            "layout": {
                "page_family_dist": {"report": 1.0},
                "family_layout_type_dist": {
                    "report": {"single_col": 1.0},
                },
                "line_gap": {
                    "randomness_percent": 0,
                },
                "occupancy": {
                    "enable": False,
                },
            },
            "page": {
                "size_dist": {
                    "a4_portrait": 1.0,
                },
            },
            "render": {
                "non_text": {
                    "table_shape": {
                        "min_rows": 2,
                        "max_rows": 5,
                        "min_cols": 2,
                        "max_cols": 4,
                    }
                }
            },
        }
    )


def _assert_bbox_inside_page(bbox, w: int, h: int) -> None:
    x, y, bw, bh = bbox

    assert bw > 0
    assert bh > 0
    assert 0 <= x < w
    assert 0 <= y < h
    assert x + bw <= w
    assert y + bh <= h


def test_overlap_ratio_min_area_xywh():
    assert _overlap_ratio_min_area_xywh((0, 0, 10, 10), (20, 20, 10, 10)) == 0.0
    assert _overlap_ratio_min_area_xywh((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0

    partial = _overlap_ratio_min_area_xywh((0, 0, 10, 10), (5, 0, 10, 10))
    assert 0.0 < partial < 1.0


def test_box_too_close_or_overlapping_respects_gap_and_overlap():
    accepted = [(0, 0, 10, 10)]

    assert _box_too_close_or_overlapping(
        (5, 0, 10, 10),
        accepted,
        max_overlap_ratio=0.1,
        min_gap_px=0,
    ) is True

    assert _box_too_close_or_overlapping(
        (12, 0, 10, 10),
        accepted,
        max_overlap_ratio=0.1,
        min_gap_px=4,
    ) is True

    assert _box_too_close_or_overlapping(
        (30, 30, 10, 10),
        accepted,
        max_overlap_ratio=0.1,
        min_gap_px=4,
    ) is False


def test_clamp_block_xy_keeps_block_inside_page_margins():
    x, y = _clamp_block_xy(
        -100,
        9999,
        200,
        200,
        w=1000,
        h=1200,
        margin_x=50,
        margin_y=60,
    )

    assert 50 <= x <= 1000 - 50 - 200
    assert 60 <= y <= 1200 - 60 - 200


def test_target_counts_uses_density_targets_and_family_scaling():
    cfg = DummyCfg()
    rng = random.Random(123)

    lines, blocks = _target_counts(
        cfg,
        density_level="normal",
        page_family="report",
        rng=rng,
    )

    assert 4 <= lines <= 18
    assert 1 <= blocks <= 6


def test_resolve_block_overlaps_after_occupancy_keeps_count_and_bounds():
    placed = [
        (0, 80, 80, 500, 300, "paragraph", {}),
        (0, 90, 90, 500, 300, "paragraph", {}),
        (0, 100, 100, 500, 300, "table", {}),
    ]

    out = _resolve_block_overlaps_after_occupancy(
        placed=placed,
        w=1200,
        h=1600,
        rng=random.Random(123),
        layout_cfg={
            "occupancy": {
                "final_overlap_resolve_attempts": 64,
                "final_min_gap_px": 8,
                "final_max_overlap_ratio_min_area": 0.08,
            }
        },
    )

    assert len(out) == len(placed)

    for item in out:
        _col, x, y, bw, bh, _block_type, _style = item
        _assert_bbox_inside_page((x, y, bw, bh), 1200, 1600)


def test_sample_page_spec_returns_valid_pagespec_contract():
    page = sample_page_spec(
        _cfg_text_only(),
        random.Random(123),
        page_index=0,
        page_id="000001",
    )

    assert isinstance(page, PageSpec)
    assert page.page_id == "000001"
    assert page.w > 0
    assert page.h > 0
    assert page.dpi == 200
    assert page.page_size_name == "a4_portrait"
    assert page.orientation == "portrait"
    assert page.page_family == "report"
    assert page.layout_type == "single_col"
    assert page.density_level == "normal"
    assert page.noise_level == "clean"

    assert page.blocks
    assert page.lines

    assert all(isinstance(block, BlockSpec) for block in page.blocks)
    assert all(isinstance(line, LineSpec) for line in page.lines)

    block_ids = {block.block_id for block in page.blocks}

    for block in page.blocks:
        _assert_bbox_inside_page(block.bbox, page.w, page.h)
        assert block.block_order == block.block_id
        assert isinstance(block.style, dict)

    for idx, line in enumerate(page.lines):
        _assert_bbox_inside_page(line.bbox, page.w, page.h)
        assert line.global_line_order == idx
        assert line.block_id in block_ids
        assert line.line_type in {"text", "caption", "math", "table_cell"}

    assert page.has_table == any(block.block_type == "table" for block in page.blocks)
    assert page.has_equation == any(block.block_type == "equation" for block in page.blocks)
    assert page.has_figure == any(block.block_type == "figure" for block in page.blocks)


def test_sample_page_spec_global_line_order_is_contiguous_across_multiple_pages():
    cfg = _cfg_text_only()

    for seed in range(10):
        page = sample_page_spec(
            cfg,
            random.Random(seed),
            page_index=seed,
            page_id=f"{seed:06d}",
        )

        orders = [line.global_line_order for line in page.lines]

        assert orders == list(range(len(orders)))