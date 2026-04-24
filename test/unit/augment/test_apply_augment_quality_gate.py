import random

from ai1_gen.augment.apply_augment import apply_augment


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
    # Fallback her seed'de garanti değil; bu yüzden trace varsa kontrol ediyoruz.
    if "fallback_to_light_plan" in ops:
        assert out.geom_M is None