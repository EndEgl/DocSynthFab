from __future__ import annotations

import random

import pytest

from ai1_gen.augment.apply_augment import apply_augment
from ai1_gen.cli import _make_fallback_render
from ai1_gen.qc.validators import validate_page


class CfgStub:
    version = "ai1-ds-v1.3.2"

    def __init__(self):
        self.raw = {"page": {"bg_color_rgb": [255, 255, 255]}}

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


def _base_aug_cfg():
    return {
        "selection_policy": {
            "clean": {
                "p_photometric": 0.0,
                "p_blur_noise": 0.0,
                "p_capture": 0.0,
                "p_geometry": 0.0,
                "p_edge": 0.0,
                "p_elastic": 0.0,
            }
        },
        "photometric": {},
        "blur_noise": {},
        "capture_sim": {},
        "geometry": {},
        "edge_degredation": {},
        "elastic_distortion": {},
    }


@pytest.mark.integration
def test_light_photometric_augment_still_passes_qc():
    cfg = CfgStub()
    rr = _make_fallback_render(cfg, page_id="000010", dpi=300)

    aug_cfg = _base_aug_cfg()
    aug_cfg["selection_policy"]["clean"]["p_photometric"] = 1.0
    aug_cfg["photometric"] = {"gamma": [1.0, 1.0], "brightness": [0, 0], "contrast": [1.0, 1.0]}

    out = apply_augment(
        rr["image_u8"],
        rr["mask_text_u8"],
        rr["mask_math_u8"],
        rr["ann"],
        rr["ann"]["meta"],
        aug_cfg,
        random.Random(123),
    )

    ok, code, extra = validate_page(out.ann_aug, out.mask_text_aug_u8, out.mask_math_aug_u8, cfg)

    assert ok is True
    assert code is None


@pytest.mark.integration
def test_capture_sim_trace_is_recorded_and_shapes_are_preserved():
    cfg = CfgStub()
    rr = _make_fallback_render(cfg, page_id="000011", dpi=300)

    meta = dict(rr["ann"]["meta"])
    meta["scale_profile"] = "lowres_capture"

    aug_cfg = _base_aug_cfg()
    aug_cfg["capture_sim"] = {
        "downscale_factor": [0.8, 0.8],
        "jpeg_quality_clean_medium": [90, 90],
        "jpeg_quality_heavy": [70, 70],
    }

    out = apply_augment(
        rr["image_u8"],
        rr["mask_text_u8"],
        rr["mask_math_u8"],
        rr["ann"],
        meta,
        aug_cfg,
        random.Random(123),
    )

    assert out.image_aug_u8.shape == rr["image_u8"].shape
    assert out.mask_text_aug_u8.shape == rr["mask_text_u8"].shape
    assert any(t["op"] == "quick_quality_gate" for t in out.aug_trace)


@pytest.mark.integration
def test_edge_degradation_keeps_output_structurally_valid():
    cfg = CfgStub()
    rr = _make_fallback_render(cfg, page_id="000012", dpi=300)

    aug_cfg = _base_aug_cfg()
    aug_cfg["selection_policy"]["clean"]["p_edge"] = 1.0
    aug_cfg["edge_degredation"] = {
        "prob": 1.0,
        "num_erasures": [1, 1],
        "size_ratio": [0.01, 0.02],
        "protect_math": True,
        "skip_if_remaining_area_lt": 1,
    }

    out = apply_augment(
        rr["image_u8"],
        rr["mask_text_u8"],
        rr["mask_math_u8"],
        rr["ann"],
        rr["ann"]["meta"],
        aug_cfg,
        random.Random(123),
    )

    assert out.image_aug_u8.shape == rr["image_u8"].shape
    assert out.ann_aug["page_id"] == rr["ann"]["page_id"]


@pytest.mark.integration
def test_heavy_degradation_records_quality_gate_or_fallback_trace():
    cfg = CfgStub()
    rr = _make_fallback_render(cfg, page_id="000013", dpi=300)

    aug_cfg = _base_aug_cfg()
    aug_cfg["selection_policy"]["clean"]["p_edge"] = 1.0
    aug_cfg["edge_degredation"] = {
        "prob": 1.0,
        "num_erasures": [3, 3],
        "size_ratio": [0.20, 0.25],
        "protect_math": False,
        "skip_if_remaining_area_lt": 1,
    }

    out = apply_augment(
        rr["image_u8"],
        rr["mask_text_u8"],
        rr["mask_math_u8"],
        rr["ann"],
        rr["ann"]["meta"],
        aug_cfg,
        random.Random(7),
    )

    ops = [t["op"] for t in out.aug_trace]
    assert "quick_quality_gate" in ops