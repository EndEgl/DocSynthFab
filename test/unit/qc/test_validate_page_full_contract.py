from __future__ import annotations

from typing import Any

import numpy as np

from docsynthfab.qc.validators import validate_page


class Cfg:
    def __init__(
        self,
        *,
        block_mix: dict[str, float] | None = None,
        qc_overrides: dict[str, Any] | None = None,
        thresholds: dict[str, Any] | None = None,
    ) -> None:
        self.raw = {
            "content": {
                "block_mix": block_mix or {"text": 100, "table": 0, "latex": 0},
            }
        }
        self._thresholds = thresholds or {}

        base_qc = {
            "mask_binary_required": True,
            "overlap_text_over_math_max_ratio": 0.01,
            "require_global_line_order_contiguous": True,
            "require_content_purity_contract": True,
            "reject_tofu_text_chars": True,
            "reject_code_token_leakage": True,
            "max_code_token_leak_count": 0,
            "require_title_near_top": False,
            "require_caption_near_target": False,
            "use_page_family_rules": False,
            "soft_reading_order_check": False,
            "max_block_overlap_ratio_min_area": 0.35,
            "visual_coverage": {"enable": False},
            "density": {
                "use_eligible_area_excluding_figures": True,
                "use_content_union_if_equation": True,
                "density_soft_margin_abs": 0.0025,
                "allow_density_remap": True,
            },
        }

        if qc_overrides:
            for key, value in qc_overrides.items():
                if isinstance(value, dict) and isinstance(base_qc.get(key), dict):
                    merged = dict(base_qc[key])
                    merged.update(value)
                    base_qc[key] = merged
                else:
                    base_qc[key] = value

        self._qc = base_qc

    def qc(self) -> dict[str, Any]:
        return self._qc

    def thresholds(self) -> dict[str, Any]:
        return self._thresholds


def _base_ann() -> dict[str, Any]:
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
        "blocks": [
            {"block_id": 0, "block_type": "paragraph", "bbox": [10, 10, 150, 30]},
        ],
        "lines": [
            {
                "line_id": 0,
                "block_id": 0,
                "line_type": "text",
                "line_order_in_block": 0,
                "global_line_order": 0,
                "bbox": [15, 15, 120, 12],
                "gt_text": "clean text",
                "gt_script": "latin",
            }
        ],
        "gt_stats": {},
    }


def _mask_text() -> np.ndarray:
    m = np.zeros((100, 200), dtype=np.uint8)
    m[15:35, 15:135] = 255
    return m


def _mask_math() -> np.ndarray:
    return np.zeros((100, 200), dtype=np.uint8)


def test_validate_page_accepts_clean_text_page():
    ok, code, extra = validate_page(
        _base_ann(),
        _mask_text(),
        _mask_math(),
        Cfg(),
    )

    assert ok is True
    assert code is None
    assert "overlap_ratio" in extra


def test_validate_page_rejects_non_binary_mask():
    bad = _mask_text()
    bad[0, 0] = 128

    ok, code, extra = validate_page(
        _base_ann(),
        bad,
        _mask_math(),
        Cfg(),
    )

    assert ok is False
    assert code == "qc/mask-not-binary"


def test_validate_page_rejects_text_math_overlap():
    text = _mask_text()
    math = np.zeros((100, 200), dtype=np.uint8)
    math[15:35, 15:135] = 255

    ok, code, extra = validate_page(
        _base_ann(),
        text,
        math,
        Cfg(),
    )

    assert ok is False
    assert code == "qc/overlap-too-high"
    assert extra["overlap_ratio"] >= 0.01


def test_validate_page_rejects_non_contiguous_global_line_order():
    ann = _base_ann()
    ann["lines"][0]["global_line_order"] = 1

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(),
    )

    assert ok is False
    assert code == "qc/order-not-contiguous"
    assert extra["expected"] == 0
    assert extra["found"] == 1


def test_validate_page_rejects_bbox_outside_page():
    ann = _base_ann()
    ann["blocks"][0]["bbox"] = [-1, 10, 150, 30]

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(),
    )

    assert ok is False
    assert code == "qc/bbox-outside-page"
    assert extra["kind"] == "blocks"


def test_validate_page_rejects_code_token_leakage():
    ann = _base_ann()
    ann["lines"][0]["gt_text"] = "bad cfg.size bbox::seed leaked"

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(),
    )

    assert ok is False
    assert code == "qc/code-token-leakage-detected"
    assert extra["code_token_leak_count"] >= 2


def test_validate_page_rejects_visual_coverage_too_low():
    ann = _base_ann()
    ann["blocks"][0]["bbox"] = [10, 10, 20, 20]
    ann["lines"][0]["bbox"] = [10, 10, 10, 10]

    ok, code, extra = validate_page(
        ann,
        np.zeros((100, 200), dtype=np.uint8),
        np.zeros((100, 200), dtype=np.uint8),
        Cfg(
            qc_overrides={
                "visual_coverage": {
                    "enable": True,
                    "min_content_ratio_by_density": {"normal": 0.50},
                    "min_bbox_extent_ratio_by_density": {"normal": 0.50},
                }
            }
        ),
    )

    assert ok is False
    assert code == "qc/visual-coverage-too-low"


def test_validate_page_rejects_invalid_line_bbox():
    ann = _base_ann()
    ann["lines"][0]["bbox"] = [15, 15, 2, 2]

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(),
    )

    assert ok is False
    assert code == "qc/invalid-line-bbox"
    assert extra["reason"] == "too-small-line-bbox"


def test_validate_page_rejects_block_overlap_too_high():
    ann = _base_ann()
    ann["blocks"] = [
        {"block_id": 0, "block_type": "paragraph", "bbox": [10, 10, 100, 40]},
        {"block_id": 1, "block_type": "paragraph", "bbox": [20, 15, 100, 40]},
    ]
    ann["lines"] = [
        {
            "line_id": 0,
            "block_id": 0,
            "line_type": "text",
            "line_order_in_block": 0,
            "global_line_order": 0,
            "bbox": [15, 15, 80, 10],
            "gt_text": "clean one",
            "gt_script": "latin",
        },
        {
            "line_id": 1,
            "block_id": 1,
            "line_type": "text",
            "line_order_in_block": 0,
            "global_line_order": 1,
            "bbox": [25, 30, 80, 10],
            "gt_text": "clean two",
            "gt_script": "latin",
        },
    ]

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(),
    )

    assert ok is False
    assert code == "qc/block-overlap-too-high"


def test_validate_page_rejects_title_too_low_when_required():
    ann = _base_ann()
    ann["blocks"] = [
        {"block_id": 0, "block_type": "title", "bbox": [10, 50, 150, 20]},
    ]
    ann["lines"][0]["block_id"] = 0
    ann["lines"][0]["bbox"] = [15, 55, 120, 10]

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(qc_overrides={"require_title_near_top": True}),
    )

    assert ok is False
    assert code == "qc/title-too-low"


def test_validate_page_rejects_caption_without_target_when_required():
    ann = _base_ann()
    ann["blocks"] = [
        {"block_id": 0, "block_type": "caption", "bbox": [10, 10, 150, 20]},
    ]
    ann["lines"][0]["line_type"] = "caption"

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(
            block_mix={"text": 50, "table": 50, "latex": 0},
            qc_overrides={"require_caption_near_target": True},
        ),
    )

    assert ok is False
    assert code == "qc/caption-placement-invalid"


def test_validate_page_rejects_page_family_missing_title_when_enabled():
    ann = _base_ann()
    ann["meta"]["page_family"] = "report"
    ann["meta"]["content_pure_mode"] = "mixed"

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(qc_overrides={"use_page_family_rules": True}),
    )

    assert ok is False
    assert code == "qc/page-family-rule-failed"
    assert extra["reason"] == "missing-title"


def test_validate_page_rejects_suspicious_reading_order_when_enabled():
    ann = _base_ann()
    ann["blocks"] = [
        {"block_id": 0, "block_type": "paragraph", "bbox": [10, 5, 150, 90]},
    ]
    ann["lines"] = []

    for i in range(12):
        y = 80 if i % 2 == 0 else 10
        ann["lines"].append(
            {
                "line_id": i,
                "block_id": 0,
                "line_type": "text",
                "line_order_in_block": i,
                "global_line_order": i,
                "bbox": [15, y, 120, 6],
                "gt_text": f"clean line {i}",
                "gt_script": "latin",
            }
        )

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(qc_overrides={"soft_reading_order_check": True}),
    )

    assert ok is False
    assert code == "qc/reading-order-suspicious"


def test_validate_page_rejects_density_out_of_range_when_remap_disabled():
    ann = _base_ann()

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(
            qc_overrides={
                "density": {
                    "allow_density_remap": False,
                    "density_soft_margin_abs": 0.0,
                }
            },
            thresholds={
                "ink_ratio_text_ranges": {
                    "normal": [0.90, 1.00],
                }
            },
        ),
    )

    assert ok is False
    assert code == "qc/density-out-of-range"


def test_validate_page_can_remap_density_bucket():
    ann = _base_ann()

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(
            qc_overrides={
                "density": {
                    "allow_density_remap": True,
                    "density_soft_margin_abs": 0.0,
                }
            },
            thresholds={
                "ink_ratio_text_ranges": {
                    "sparse": [0.00, 0.20],
                    "normal": [0.90, 1.00],
                }
            },
        ),
    )

    assert ok is True
    assert code is None
    assert ann["meta"]["density_level"] == "sparse"
    assert extra["density_remap_from"] == "normal"
    assert extra["density_remap_to"] == "sparse"


def test_validate_page_rejects_mixed_variance_too_low():
    ann = _base_ann()
    ann["meta"]["density_level"] = "mixed"

    ok, code, extra = validate_page(
        ann,
        np.zeros((100, 200), dtype=np.uint8),
        np.zeros((100, 200), dtype=np.uint8),
        Cfg(
            qc_overrides={
                "density": {
                    "use_eligible_area_excluding_figures": False,
                }
            },
            thresholds={
                "mixed": {
                    "bands": 8,
                    "variance_thr": 0.00010,
                }
            },
        ),
    )

    assert ok is False
    assert code == "qc/mixed-variance-too-low"


def test_validate_page_rejects_scale_profile_dpi_mismatch():
    ann = _base_ann()
    ann["meta"]["scale_profile"] = "dpi200"
    ann["size"]["dpi"] = 300

    ok, code, extra = validate_page(
        ann,
        _mask_text(),
        _mask_math(),
        Cfg(),
    )

    assert ok is False
    assert code == "qc/scale-profile-mismatch"
    assert extra["scale_profile"] == "dpi200"
    assert extra["dpi"] == 300