import random

from ai1_gen.augment.apply_augment import _clip_bbox_xywh, apply_augment


def test_clip_bbox_xywh_clamps_to_canvas():
    clipped = _clip_bbox_xywh([-5, -2, 200, 100], 50, 40)

    assert clipped[0] == 0
    assert clipped[1] == 0
    assert clipped[2] <= 50
    assert clipped[3] <= 40


def test_apply_augment_enforces_capture_for_lowres_profile(
    rgb_image_u8,
    mask_text_u8,
    ann_minimal_dict,
):
    mask_math = mask_text_u8 * 0
    rng = random.Random(123)

    meta = dict(ann_minimal_dict["meta"])
    meta["scale_profile"] = "lowres_capture"

    aug_cfg = {
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
        "capture_sim": {
            "downscale_factor": [0.8, 0.8],
            "jpeg_quality_clean_medium": [90, 90],
            "jpeg_quality_heavy": [70, 70],
        },
        "geometry": {},
        "edge_degredation": {},
        "elastic_distortion": {},
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

    assert out.image_aug_u8.shape == rgb_image_u8.shape
    assert any(t["op"] == "quick_quality_gate" for t in out.aug_trace)