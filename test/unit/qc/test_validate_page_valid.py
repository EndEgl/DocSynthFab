from ai1_gen.qc.validators import validate_page


def test_validate_page_accepts_minimal_valid_page(dummy_cfg, ann_minimal_dict, mask_text_u8):
    mask_math = mask_text_u8 * 0
    ok, code, extra = validate_page(ann_minimal_dict, mask_text_u8, mask_math, dummy_cfg)

    assert ok is True
    assert code is None
    assert isinstance(extra, dict)
    assert "ink_ratio_content" in extra
    assert "ink_ratio_math" in extra
    assert extra["ink_ratio_math"] == 0.0