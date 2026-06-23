from __future__ import annotations

import random

from docsynthfab.layout.occupancy import (
    OccupancyRect,
    PageOccupancy,
    occupancy_cfg,
    refine_block_positions_with_occupancy,
    target_fill_ratio_for_density,
)


def test_occupancy_rect_properties():
    rect = OccupancyRect(x=10, y=20, w=30, h=40, kind="paragraph")

    assert rect.x1 == 40
    assert rect.y1 == 60
    assert rect.area == 1200
    assert rect.center == (25.0, 40.0)


def test_page_occupancy_fill_ratio_and_overlap_with_gap():
    occ = PageOccupancy(100, 100, min_gap_px=5)

    first = OccupancyRect(10, 10, 20, 20)
    second_far = OccupancyRect(60, 60, 20, 20)
    second_close = OccupancyRect(32, 10, 20, 20)

    occ.add(first)

    assert round(occ.fill_ratio(), 4) == 0.04
    assert occ.overlaps(second_far) is False
    assert occ.overlaps(second_close) is True


def test_page_occupancy_score_rejects_out_of_page_candidate():
    occ = PageOccupancy(100, 100, min_gap_px=0)

    good = OccupancyRect(10, 10, 20, 20)
    bad = OccupancyRect(90, 90, 20, 20)

    assert occ.score_candidate(good, spread_percent=50, rng=random.Random(123)) > -1e18
    assert occ.score_candidate(bad, spread_percent=50, rng=random.Random(123)) == -1e18


def test_occupancy_cfg_defaults_and_custom_values():
    default = occupancy_cfg({})

    assert default["enable"] is True
    assert default["whitespace_strategy"] == "balanced"
    assert default["spread_percent"] == 65.0
    assert default["min_gap_px"] == 12

    custom = occupancy_cfg(
        {
            "occupancy": {
                "enable": False,
                "whitespace_strategy": "compact",
                "spread_percent": 80,
                "min_gap_px": 20,
                "max_place_attempts": 10,
                "target_fill_ratio": {"normal": [0.3, 0.5]},
            }
        }
    )

    assert custom["enable"] is False
    assert custom["whitespace_strategy"] == "compact"
    assert custom["spread_percent"] == 80.0
    assert custom["min_gap_px"] == 20
    assert custom["max_place_attempts"] == 10
    assert custom["target_fill_ratio"] == {"normal": [0.3, 0.5]}


def test_target_fill_ratio_for_density_uses_custom_range():
    value = target_fill_ratio_for_density(
        "normal",
        {
            "target_fill_ratio": {
                "normal": [0.30, 0.40],
            }
        },
        random.Random(123),
    )

    assert 0.30 <= value <= 0.40


def test_refine_block_positions_with_occupancy_returns_original_when_disabled():
    placed = [
        (0, 100, 100, 300, 200, "paragraph", {}),
        (0, 100, 340, 300, 200, "list", {}),
    ]

    out = refine_block_positions_with_occupancy(
        placed=placed,
        w=1000,
        h=1200,
        density_level="normal",
        layout_cfg={
            "occupancy": {
                "enable": False,
            }
        },
        rng=random.Random(123),
    )

    assert out == placed


def test_refine_block_positions_with_occupancy_keeps_count_and_page_bounds():
    placed = [
        (-1, 80, 80, 840, 120, "title", {"full_width": True}),
        (0, 80, 240, 360, 260, "paragraph", {}),
        (1, 520, 240, 360, 260, "table", {}),
        (0, 80, 540, 360, 180, "list", {}),
    ]

    out = refine_block_positions_with_occupancy(
        placed=placed,
        w=1000,
        h=1200,
        density_level="normal",
        layout_cfg={
            "occupancy": {
                "enable": True,
                "whitespace_strategy": "balanced",
                "spread_percent": 60,
                "min_gap_px": 8,
                "max_place_attempts": 16,
                "target_fill_ratio": {
                    "normal": [0.20, 0.35],
                },
            }
        },
        rng=random.Random(123),
    )

    assert len(out) == len(placed)

    for col, x, y, bw, bh, block_type, style in out:
        assert col in {-1, 0, 1}
        assert bw > 0
        assert bh > 0
        assert 0 <= x < 1000
        assert 0 <= y < 1200
        assert x + bw <= 1000
        assert y + bh <= 1200
        assert isinstance(block_type, str)
        assert isinstance(style, dict)