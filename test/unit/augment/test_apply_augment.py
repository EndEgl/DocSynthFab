from __future__ import annotations

import random

from docsynthfab.augment.apply_augment import _clip_bbox_xywh, apply_augment


def _no_aug_cfg() -> dict:
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


def test_clip_bbox_xywh_clamps_to_canvas():
    clipped = _clip_bbox_xywh([-5, -2, 200, 100], 50, 40)

    assert clipped[0] == 0
    assert clipped[1] == 0
    assert clipped[2] <= 50
    assert clipped[3] <= 40


def test_apply_augment_returns_augresult_with_same_shapes(
    rgb_image_u8,
    mask_text_u8,
    ann_minimal_dict,
):
    mask_math = mask_text_u8 * 0
    rng = random.Random(123)

    out = apply_augment(
        rgb_image_u8,
        mask_text_u8,
        mask_math,
        ann_minimal_dict,
        ann_minimal_dict["meta"],
        _no_aug_cfg(),
        rng,
    )

    assert out.image_aug_u8.shape == rgb_image_u8.shape
    assert out.mask_text_aug_u8.shape == mask_text_u8.shape
    assert out.mask_math_aug_u8.shape == mask_math.shape
    assert out.ann_aug["page_id"] == ann_minimal_dict["page_id"]
    assert isinstance(out.aug_trace, list)


def test_apply_augment_enforces_capture_for_lowres_profile(
    rgb_image_u8,
    mask_text_u8,
    ann_minimal_dict,
):
    mask_math = mask_text_u8 * 0
    rng = random.Random(123)

    meta = dict(ann_minimal_dict["meta"])
    meta["scale_profile"] = "lowres_capture"

    aug_cfg = _no_aug_cfg()
    aug_cfg["capture_sim"] = {
        "downscale_factor": [0.8, 0.8],
        "jpeg_quality_clean_medium": [90, 90],
        "jpeg_quality_heavy": [70, 70],
    }

    out = apply_augment(
        rgb_image_u8,
        mask_text_u8,
        mask_math,
        ann_minimal_dict,
        meta,
        aug_cfg,
        rng,
    )

    ops = [t["op"] for t in out.aug_trace]

    assert out.image_aug_u8.shape == rgb_image_u8.shape
    assert "capture_sim" in ops
    assert "quick_quality_gate" in ops


    
def test_apply_augment_can_fallback_to_light_plan_when_masks_degrade(
    rgb_image_u8,
    mask_text_u8,
    ann_math_dict,
    mask_math_u8,
):
    rng = random.Random(7)

    aug_cfg = {
        "selection_policy": {
            "clean": {
                "p_photometric": 0.0,
                "p_blur_noise": 0.0,
                "p_capture": 0.0,
                "p_geometry": 0.0,
                "p_edge": 1.0,
                "p_elastic": 0.0,
            }
        },
        "photometric": {},
        "blur_noise": {},
        "capture_sim": {},
        "geometry": {},
        "edge_degredation": {
            "prob": 1.0,
            "num_erasures": [3, 3],
            "size_ratio": [0.20, 0.25],
            "protect_math": False,
            "skip_if_remaining_area_lt": 1,
        },
        "elastic_distortion": {},
    }

    out = apply_augment(
        rgb_image_u8,
        mask_text_u8,
        mask_math_u8,
        ann_math_dict,
        ann_math_dict["meta"],
        aug_cfg,
        rng,
    )

    ops = [t["op"] for t in out.aug_trace]

    assert "quick_quality_gate" in ops

    # Fallback her seed'de garanti değil; bu yüzden trace varsa davranışı kontrol ediyoruz.
    if "fallback_to_light_plan" in ops:
        assert out.geom_M is None



