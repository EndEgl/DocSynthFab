from __future__ import annotations

from docsynthfab.qc.layout_rules import (
    _collect_blocks_by_type,
    _validate_block_overlaps,
    _validate_caption_proximity,
    _validate_line_boxes,
    _validate_page_family_rules,
    _validate_reading_order_soft,
    _validate_title_position,
)


def test_collect_blocks_by_type_groups_blocks():
    ann = {
        "blocks": [
            {"block_type": "title", "block_id": 0},
            {"block_type": "paragraph", "block_id": 1},
            {"block_type": "paragraph", "block_id": 2},
        ]
    }

    grouped = _collect_blocks_by_type(ann)

    assert len(grouped["title"]) == 1
    assert len(grouped["paragraph"]) == 2


def test_validate_block_overlaps_rejects_large_overlap():
    ann = {
        "blocks": [
            {"block_id": 0, "block_type": "paragraph", "bbox": [10, 10, 100, 60]},
            {"block_id": 1, "block_type": "table", "bbox": [20, 20, 100, 60]},
        ]
    }

    ok, extra = _validate_block_overlaps(ann, max_iou_like=0.35)

    assert ok is False
    assert extra["block_a_id"] == 0
    assert extra["block_b_id"] == 1
    assert extra["overlap_ratio_min_area"] > 0.35


def test_validate_block_overlaps_ignores_caption_overlap():
    ann = {
        "blocks": [
            {"block_id": 0, "block_type": "table", "bbox": [10, 10, 100, 60]},
            {"block_id": 1, "block_type": "caption", "bbox": [10, 10, 100, 60]},
        ]
    }

    ok, extra = _validate_block_overlaps(ann, max_iou_like=0.35)

    assert ok is True
    assert extra is None


def test_validate_title_position_rejects_low_title():
    ann = {
        "blocks": [
            {"block_id": 0, "block_type": "title", "bbox": [10, 40, 100, 20]},
        ]
    }

    ok, extra = _validate_title_position(ann, H=100)

    assert ok is False
    assert extra["title_block_id"] == 0


def test_validate_title_position_accepts_top_title():
    ann = {
        "blocks": [
            {"block_id": 0, "block_type": "title", "bbox": [10, 10, 100, 20]},
        ]
    }

    ok, extra = _validate_title_position(ann, H=100)

    assert ok is True
    assert extra is None


def test_validate_caption_proximity_rejects_caption_without_target():
    ann = {
        "blocks": [
            {"block_id": 0, "block_type": "caption", "bbox": [10, 10, 100, 20]},
        ]
    }

    ok, extra = _validate_caption_proximity(ann)

    assert ok is False
    assert extra["reason"] == "caption-exists-without-figure-or-table"


def test_validate_caption_proximity_accepts_near_table_caption():
    ann = {
        "blocks": [
            {"block_id": 0, "block_type": "table", "bbox": [10, 10, 120, 60]},
            {"block_id": 1, "block_type": "caption", "bbox": [10, 75, 120, 15]},
        ]
    }

    ok, extra = _validate_caption_proximity(ann)

    assert ok is True
    assert extra is None


def test_validate_line_boxes_rejects_tiny_line_bbox():
    ann = {
        "lines": [
            {"line_id": 0, "bbox": [10, 10, 3, 20]},
        ]
    }

    ok, extra = _validate_line_boxes(ann)

    assert ok is False
    assert extra["reason"] == "too-small-line-bbox"


def test_validate_reading_order_soft_rejects_too_many_backward_jumps():
    lines = []

    for i in range(12):
        y = 80 if i % 2 == 0 else 10
        lines.append(
            {
                "line_id": i,
                "global_line_order": i,
                "bbox": [10, y, 100, 8],
            }
        )

    ok, extra = _validate_reading_order_soft({"lines": lines})

    assert ok is False
    assert extra["backward_jumps"] > 4


def test_validate_page_family_rules_rejects_missing_title_for_report():
    ann = {
        "meta": {
            "page_family": "report",
            "content_pure_mode": "mixed",
            "_fallback": False,
        },
        "blocks": [
            {"block_type": "paragraph", "bbox": [10, 10, 100, 20]},
        ],
    }

    ok, extra = _validate_page_family_rules(ann)

    assert ok is False
    assert extra["reason"] == "missing-title"


def test_validate_page_family_rules_skips_table_only_mode():
    ann = {
        "meta": {
            "page_family": "report",
            "content_pure_mode": "table_only",
            "_fallback": False,
        },
        "blocks": [
            {"block_type": "table", "bbox": [10, 10, 100, 20]},
        ],
    }

    ok, extra = _validate_page_family_rules(ann)

    assert ok is True
    assert extra is None