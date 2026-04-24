import numpy as np

from ai1_gen.qc.validators import validate_page


def test_validate_page_rejects_non_binary_masks(dummy_cfg, ann_minimal_dict, mask_text_u8):
    bad_mask = mask_text_u8.copy()
    bad_mask[0, 0] = 7
    mask_math = np.zeros_like(mask_text_u8)

    ok, code, extra = validate_page(ann_minimal_dict, bad_mask, mask_math, dummy_cfg)

    assert ok is False
    assert code == "qc/mask-not-binary"


def test_validate_page_rejects_overlap_too_high(dummy_cfg, ann_minimal_dict, mask_text_u8):
    mask_math = mask_text_u8.copy()

    ok, code, extra = validate_page(ann_minimal_dict, mask_text_u8, mask_math, dummy_cfg)

    assert ok is False
    assert code == "qc/overlap-too-high"
    assert "overlap_ratio" in extra


def test_validate_page_rejects_non_contiguous_order(dummy_cfg, ann_minimal_dict, mask_text_u8):
    ann_minimal_dict["lines"][0]["global_line_order"] = 99
    mask_math = np.zeros_like(mask_text_u8)

    ok, code, extra = validate_page(ann_minimal_dict, mask_text_u8, mask_math, dummy_cfg)

    assert ok is False
    assert code == "qc/order-not-contiguous"
    assert extra["expected"] == 0
    assert extra["found"] == 99


def test_validate_page_rejects_invalid_line_bbox(dummy_cfg, ann_minimal_dict, mask_text_u8):
    ann_minimal_dict["lines"][0]["bbox"] = [10, 10, -5, 20]
    mask_math = np.zeros_like(mask_text_u8)

    ok, code, extra = validate_page(ann_minimal_dict, mask_text_u8, mask_math, dummy_cfg)

    assert ok is False
    assert code == "qc/invalid-line-bbox"