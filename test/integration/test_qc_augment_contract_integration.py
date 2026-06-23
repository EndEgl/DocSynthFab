from __future__ import annotations

import copy
import random

import pytest

from docsynthfab.augment.apply_augment import apply_augment
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
            "require_content_purity_contract": True,
            "reject_tofu_text_chars": True,
            "reject_code_token_leakage": True,
            "max_code_token_leak_count": 0,
            "require_title_near_top": False,
            "require_caption_near_target": False,
            "use_page_family_rules": False,
            "soft_reading_order_check": False,
            "max_block_overlap_ratio_min_area": 0.35,
            "visual_coverage": {"enable": False},
        }

    def thresholds(self):
        return {}


def _neutral_aug_cfg():
    return {
        "selection_policy": {
            "clean": {
                "p_photometric": 1.0,
                "p_blur_noise": 0.0,
                "p_capture": 0.0,
                "p_geometry": 0.0,
                "p_edge": 0.0,
                "p_elastic": 0.0,
            }
        },
        "photometric": {
            "gamma": [1.0, 1.0],
            "brightness": [0, 0],
            "contrast": [1.0, 1.0],
        },
        "blur_noise": {},
        "capture_sim": {},
        "geometry": {},
        "edge_degredation": {},
        "elastic_distortion": {},
    }


@pytest.mark.integration
def test_fallback_render_passes_qc_then_light_augment_preserves_qc():
    cfg = CfgStub()
    rr = _make_fallback_render(cfg, page_id="000001", dpi=300)

    ok, code, extra = validate_page(
        rr["ann"],
        rr["mask_text_u8"],
        rr["mask_math_u8"],
        cfg,
    )

    assert ok is True
    assert code is None

    out = apply_augment(
        rr["image_u8"],
        rr["mask_text_u8"],
        rr["mask_math_u8"],
        rr["ann"],
        rr["ann"]["meta"],
        _neutral_aug_cfg(),
        random.Random(123),
    )

    ok2, code2, extra2 = validate_page(
        out.ann_aug,
        out.mask_text_aug_u8,
        out.mask_math_aug_u8,
        cfg,
    )

    assert ok2 is True
    assert code2 is None
    assert out.image_aug_u8.shape == rr["image_u8"].shape
    assert out.mask_text_aug_u8.shape == rr["mask_text_u8"].shape
    assert out.mask_math_aug_u8.shape == rr["mask_math_u8"].shape
    assert out.ann_aug["page_id"] == rr["ann"]["page_id"]
    assert any(t["op"] == "quick_quality_gate" for t in out.aug_trace)


@pytest.mark.integration
def test_qc_rejects_corrupted_annotation_after_render():
    cfg = CfgStub()
    rr = _make_fallback_render(cfg, page_id="000002", dpi=300)
    ann = copy.deepcopy(rr["ann"])

    ann["lines"][0]["bbox"] = [999999, 999999, 100, 100]

    ok, code, extra = validate_page(
        ann,
        rr["mask_text_u8"],
        rr["mask_math_u8"],
        cfg,
    )

    assert ok is False
    assert code == "qc/bbox-outside-page"