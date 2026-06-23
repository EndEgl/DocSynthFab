from __future__ import annotations

import numpy as np

from docsynthfab.qc.bbox_utils import (
    _bbox_area_xywh,
    _bbox_union_extent_ratio_from_ann,
    _clamp_bbox_xywh,
    _inter_area_xyxy,
    _xywh_to_xyxy,
)
from docsynthfab.qc.mask_checks import _is_binary_u8, _visual_content_ratio


def test_clamp_bbox_xywh_clamps_to_page_bounds():
    assert _clamp_bbox_xywh(-10, -20, 50, 40, 100, 80) == (0, 0, 50, 40)
    assert _clamp_bbox_xywh(90, 70, 50, 40, 100, 80) == (90, 70, 100, 80)


def test_xywh_to_xyxy_and_bbox_area_contract():
    assert _xywh_to_xyxy([10, 20, 30, 40]) == (10, 20, 40, 60)
    assert _bbox_area_xywh([10, 20, 30, 40]) == 1200
    assert _bbox_area_xywh([10, 20, -30, 40]) == 0


def test_inter_area_xyxy():
    assert _inter_area_xyxy((0, 0, 10, 10), (20, 20, 30, 30)) == 0
    assert _inter_area_xyxy((0, 0, 10, 10), (5, 0, 15, 10)) == 50
    assert _inter_area_xyxy((0, 0, 10, 10), (0, 0, 10, 10)) == 100


def test_bbox_union_extent_ratio_from_ann_uses_line_outer_extent():
    ann = {
        "lines": [
            {"bbox": [10, 10, 20, 10]},
            {"bbox": [50, 40, 20, 20]},
        ]
    }

    ratio = _bbox_union_extent_ratio_from_ann(ann, page_w=100, page_h=100)

    # Outer extent: x=10..70 => 60, y=10..60 => 50, area=3000 / 10000.
    assert ratio == 0.30


def test_bbox_union_extent_ratio_returns_zero_when_no_valid_lines():
    assert _bbox_union_extent_ratio_from_ann({"lines": []}, 100, 100) == 0.0
    assert _bbox_union_extent_ratio_from_ann({"lines": [{"bbox": [1, 2, 0, 4]}]}, 100, 100) == 0.0


def test_is_binary_u8_accepts_only_uint8_0_255():
    good = np.array([[0, 255], [255, 0]], dtype=np.uint8)
    bad_value = np.array([[0, 128], [255, 0]], dtype=np.uint8)
    bad_dtype = np.array([[0, 255]], dtype=np.float32)

    assert _is_binary_u8(good) is True
    assert _is_binary_u8(bad_value) is False
    assert _is_binary_u8(bad_dtype) is False


def test_visual_content_ratio_uses_union_of_text_and_math_masks():
    text = np.zeros((10, 10), dtype=np.uint8)
    math = np.zeros((10, 10), dtype=np.uint8)

    text[0:2, 0:2] = 255      # 4 px
    math[1:3, 1:3] = 255      # 4 px, overlaps 1 px with text

    ratio = _visual_content_ratio(text, math)

    assert ratio == 7 / 100