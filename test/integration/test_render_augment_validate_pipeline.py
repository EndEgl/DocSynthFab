from __future__ import annotations

import random

from ai1_gen.augment.apply_augment import apply_augment
from ai1_gen.cli import _make_fallback_render
from ai1_gen.qc.validators import validate_page


class CfgStub:
    def __init__(self) -> None:
        self.raw = {
            "page": {"bg_color_rgb": [255, 255, 255]},
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

    version = "ai1-ds-v1.3.2"


def test_render_augment_validate_pipeline_stays_valid_for_light_plan():
    cfg = CfgStub()
    rr = _make_fallback_render(cfg, page_id="000112", dpi=300)

    aug_cfg = {
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

    rng = random.Random(123)
    out = apply_augment(
        rr["image_u8"],
        rr["mask_text_u8"],
        rr["mask_math_u8"],
        rr["ann"],
        rr["ann"]["meta"],
        aug_cfg,
        rng,
    )

    ok, code, extra = validate_page(
        out.ann_aug,
        out.mask_text_aug_u8,
        out.mask_math_aug_u8,
        cfg,
    )

    assert any(t["op"] == "quick_quality_gate" for t in out.aug_trace)
    assert ok is True
    assert code is None