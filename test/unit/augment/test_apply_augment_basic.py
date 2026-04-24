import random

from ai1_gen.augment.apply_augment import apply_augment


def test_apply_augment_returns_augresult_with_same_shapes(
    rgb_image_u8,
    mask_text_u8,
    ann_minimal_dict,
):
    mask_math = mask_text_u8 * 0
    rng = random.Random(123)

    meta = ann_minimal_dict["meta"]
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
        "capture_sim": {},
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
    assert out.mask_text_aug_u8.shape == mask_text_u8.shape
    assert out.mask_math_aug_u8.shape == mask_math.shape
    assert out.ann_aug["page_id"] == ann_minimal_dict["page_id"]
    assert isinstance(out.aug_trace, list)