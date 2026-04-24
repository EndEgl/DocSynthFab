from __future__ import annotations

import numpy as np

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


def test_render_validate_pipeline_accepts_fallback_render_payload():
    cfg = CfgStub()

    rr = _make_fallback_render(cfg, page_id="000111", dpi=300)
    ok, code, extra = validate_page(
        rr["ann"],
        rr["mask_text_u8"],
        rr["mask_math_u8"],
        cfg,
    )

    assert rr["image_u8"].dtype == np.uint8
    assert rr["mask_text_u8"].dtype == np.uint8
    assert rr["mask_math_u8"].dtype == np.uint8
    assert ok is True
    assert code is None