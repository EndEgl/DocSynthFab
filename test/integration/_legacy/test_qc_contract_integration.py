from __future__ import annotations

import copy

import pytest

from docsynthfab.cli import _make_fallback_render
from docsynthfab.qc.validators import validate_page


class CfgStub:
    version = "docsynthfab-ds-v0.1"

    def __init__(self):
        self.raw = {
            "page": {"bg_color_rgb": [255, 255, 255]},
            "content": {"block_mix": {"text": 100, "table": 0, "latex": 0}},
        }

    def qc(self):
        return {
            "mask_binary_required": True,
            "overlap_text_over_math_max_ratio": 0.01,
            "require_global_line_order_contiguous": True,
            "require_title_near_top": False,
            "require_caption_near_target": False,
            "use_page_family_rules": False,
            "soft_reading_order_check": False,
            "max_block_overlap_ratio_min_area": 0.35,
        }

    def thresholds(self):
        return {}


@pytest.mark.integration
def test_qc_accepts_valid_fallback_render_payload():
    cfg = CfgStub()
    rr = _make_fallback_render(cfg, page_id="000001", dpi=300)

    ok, code, extra = validate_page(rr["ann"], rr["mask_text_u8"], rr["mask_math_u8"], cfg)

    assert ok is True
    assert code is None


@pytest.mark.integration
def test_qc_rejects_invalid_bbox_when_outside_page():
    cfg = CfgStub()
    rr = _make_fallback_render(cfg, page_id="000002", dpi=300)
    ann = copy.deepcopy(rr["ann"])

    ann["lines"][0]["bbox"] = [999999, 999999, 100, 100]

    ok, code, extra = validate_page(ann, rr["mask_text_u8"], rr["mask_math_u8"], cfg)

    assert ok is False
    assert code == "qc/bbox-outside-page"


@pytest.mark.integration
def test_qc_rejects_replacement_character_in_gt_text():
    cfg = CfgStub()
    rr = _make_fallback_render(cfg, page_id="000003", dpi=300)
    ann = copy.deepcopy(rr["ann"])

    ann["lines"][0]["gt_text"] = "broken \uFFFD text"

    ok, code, extra = validate_page(ann, rr["mask_text_u8"], rr["mask_math_u8"], cfg)

    assert ok is False
    assert code is not None


@pytest.mark.integration
def test_qc_rejects_non_binary_mask_when_required():
    cfg = CfgStub()
    rr = _make_fallback_render(cfg, page_id="000004", dpi=300)

    bad_mask = rr["mask_text_u8"].copy()
    bad_mask[0, 0] = 128

    ok, code, extra = validate_page(rr["ann"], bad_mask, rr["mask_math_u8"], cfg)

    assert ok is False
    assert code is not None



