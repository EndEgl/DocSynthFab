from __future__ import annotations

from typing import Any, Dict

import numpy as np

from docsynthfab.qc.validators import validate_page


class PureModeCfg:
    def __init__(self, block_mix: Dict[str, float]) -> None:
        self.raw = {
            "content": {
                "block_mix": block_mix,
            }
        }

    def qc(self) -> Dict[str, Any]:
        return {
            "mask_binary_required": True,
            "overlap_text_over_math_max_ratio": 0.01,
            "require_global_line_order_contiguous": True,
            "require_content_purity_contract": True,
            "reject_tofu_text_chars": True,
            "require_title_near_top": False,
            "require_caption_near_target": False,
            "use_page_family_rules": False,
            "soft_reading_order_check": False,
            "max_block_overlap_ratio_min_area": 0.35,
            "visual_coverage": {"enable": False},
        }

    def thresholds(self) -> Dict[str, Any]:
        return {}


def _base_ann() -> Dict[str, Any]:
    return {
        "version": "docsynthfab-ds-v0.1",
        "page_id": "000001",
        "size": {"w": 200, "h": 100, "dpi": 300},
        "meta": {
            "density_level": "normal",
            "scale_profile": "dpi300",
            "noise_level": "clean",
            "page_family": "report",
            "has_table": False,
            "has_equation": False,
            "has_equation_layout": False,
            "has_figure": False,
            "latex_render_error_count": 0,
            "latex_render_enabled": True,
        },
        "gt_page_text": "",
        "lines": [],
        "blocks": [],
        "gt_stats": {},
    }


def _mask_text() -> np.ndarray:
    m = np.zeros((100, 200), dtype=np.uint8)
    m[10:40, 10:160] = 255
    return m


def _mask_math() -> np.ndarray:
    m = np.zeros((100, 200), dtype=np.uint8)
    m[50:75, 20:180] = 255
    return m


def test_validate_page_table_only_accepts_table_contract():
    ann = _base_ann()
    ann["meta"]["has_table"] = True
    ann["blocks"] = [
        {"block_id": 0, "block_type": "table", "bbox": [10, 10, 150, 40]},
    ]
    ann["lines"] = [
        {
            "line_id": 0,
            "block_id": 0,
            "line_type": "table_cell",
            "line_order_in_block": 0,
            "global_line_order": 0,
            "bbox": [15, 15, 80, 18],
            "gt_text": "data 123",
            "gt_script": "latin",
        },
    ]

    mt = _mask_text()
    mm = np.zeros((100, 200), dtype=np.uint8)

    ok, code, extra = validate_page(
        ann,
        mt,
        mm,
        PureModeCfg({"text": 0, "table": 100, "latex": 0}),
    )

    assert ok is True
    assert code is None


def test_validate_page_table_only_rejects_paragraph_escape():
    ann = _base_ann()
    ann["meta"]["has_table"] = True
    ann["blocks"] = [
        {"block_id": 0, "block_type": "table", "bbox": [10, 10, 150, 40]},
        {"block_id": 1, "block_type": "paragraph", "bbox": [10, 60, 150, 20]},
    ]
    ann["lines"] = [
        {
            "line_id": 0,
            "block_id": 0,
            "line_type": "table_cell",
            "line_order_in_block": 0,
            "global_line_order": 0,
            "bbox": [15, 15, 80, 18],
            "gt_text": "data 123",
            "gt_script": "latin",
        },
        {
            "line_id": 1,
            "block_id": 1,
            "line_type": "text",
            "line_order_in_block": 0,
            "global_line_order": 1,
            "bbox": [15, 60, 80, 18],
            "gt_text": "escaped text",
            "gt_script": "latin",
        },
    ]

    mt = _mask_text()
    mm = np.zeros((100, 200), dtype=np.uint8)

    ok, code, extra = validate_page(
        ann,
        mt,
        mm,
        PureModeCfg({"text": 0, "table": 100, "latex": 0}),
    )

    assert ok is False
    assert code == "qc/content-purity-violated"
    assert "paragraph" in extra["bad_blocks"]


def test_validate_page_latex_only_rejects_render_error_fallback():
    ann = _base_ann()
    ann["meta"]["has_equation"] = True
    ann["meta"]["has_equation_layout"] = True
    ann["meta"]["latex_render_error_count"] = 1
    ann["meta"]["latex_render_errors"] = [{"error": "renderer failed"}]
    ann["blocks"] = [
        {"block_id": 0, "block_type": "equation", "bbox": [20, 20, 120, 30]},
    ]
    ann["lines"] = [
        {
            "line_id": 0,
            "block_id": 0,
            "line_type": "math",
            "line_order_in_block": 0,
            "global_line_order": 0,
            "bbox": [20, 20, 120, 30],
            "gt_latex": r"x^2+y^2=z^2",
        },
    ]

    mt = np.zeros((100, 200), dtype=np.uint8)
    mm = _mask_math()

    ok, code, extra = validate_page(
        ann,
        mt,
        mm,
        PureModeCfg({"text": 0, "table": 0, "latex": 100}),
    )

    assert ok is False
    assert code == "qc/content-purity-violated"
    assert extra["reason"] == "latex-render-failed-in-latex-only-mode"


def test_validate_page_text_only_rejects_equation_escape():
    ann = _base_ann()
    ann["meta"]["has_equation"] = True
    ann["meta"]["has_equation_layout"] = True
    ann["blocks"] = [
        {"block_id": 0, "block_type": "equation", "bbox": [20, 20, 120, 30]},
    ]
    ann["lines"] = [
        {
            "line_id": 0,
            "block_id": 0,
            "line_type": "math",
            "line_order_in_block": 0,
            "global_line_order": 0,
            "bbox": [20, 20, 120, 30],
            "gt_latex": r"x+y=0",
        },
    ]

    mt = np.zeros((100, 200), dtype=np.uint8)
    mm = _mask_math()

    ok, code, extra = validate_page(
        ann,
        mt,
        mm,
        PureModeCfg({"text": 100, "table": 0, "latex": 0}),
    )

    assert ok is False
    assert code == "qc/content-purity-violated"
    assert "equation" in extra["bad_blocks"]


def test_validate_page_rejects_tofu_text_chars():
    ann = _base_ann()
    ann["blocks"] = [
        {"block_id": 0, "block_type": "paragraph", "bbox": [10, 10, 150, 30]},
    ]
    ann["lines"] = [
        {
            "line_id": 0,
            "block_id": 0,
            "line_type": "text",
            "line_order_in_block": 0,
            "global_line_order": 0,
            "bbox": [10, 10, 150, 30],
            "gt_text": "bad □ text",
            "gt_script": "latin",
        },
    ]

    mt = _mask_text()
    mm = np.zeros((100, 200), dtype=np.uint8)

    ok, code, extra = validate_page(
        ann,
        mt,
        mm,
        PureModeCfg({"text": 100, "table": 0, "latex": 0}),
    )

    assert ok is False
    assert code == "qc/text-tofu-char-detected"
    assert extra["bad_line_count"] == 1



