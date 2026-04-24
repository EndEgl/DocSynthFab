import numpy as np

from ai1_gen.cli import _make_fallback_render


def test_make_fallback_render_creates_minimal_valid_payload(dummy_cfg):
    rr = _make_fallback_render(dummy_cfg, page_id="000123", dpi=300)

    assert set(rr.keys()) == {"image_u8", "mask_text_u8", "mask_math_u8", "ann"}
    assert rr["image_u8"].dtype == np.uint8
    assert rr["mask_text_u8"].dtype == np.uint8
    assert rr["mask_math_u8"].dtype == np.uint8

    ann = rr["ann"]
    assert ann["page_id"] == "000123"
    assert ann["meta"]["_fallback"] is True
    assert ann["meta"]["scale_profile"] == "dpi300"
    assert ann["meta"]["mask_text_nonzero"] > 0
    assert ann["meta"]["mask_math_nonzero"] == 0


def test_make_fallback_render_uses_lower_resolution_for_200dpi(dummy_cfg):
    rr = _make_fallback_render(dummy_cfg, page_id="000123", dpi=200)

    image = rr["image_u8"]
    ann = rr["ann"]

    assert image.shape[:2] == (2339, 1654)
    assert ann["size"]["dpi"] == 200
    assert ann["meta"]["scale_profile"] == "dpi200"