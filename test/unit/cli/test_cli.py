from __future__ import annotations

import numpy as np

from docsynthfab.cli import (
    _build_gt_export,
    _make_fallback_render,
    _normalized_split_ratios,
    _split_of,
)


# ======================================================================================
# _make_fallback_render
# ======================================================================================

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


# ======================================================================================
# _build_gt_export
# ======================================================================================

def test_build_gt_export_keeps_line_text_and_meta(ann_minimal_dict):
    gt = _build_gt_export(ann_minimal_dict)

    assert gt["page_id"] == ann_minimal_dict["page_id"]
    assert gt["size"]["w"] == 200
    assert gt["meta"]["has_equation"] is False
    assert gt["lines"][0]["text"] == "Hello world"
    assert gt["lines"][0]["script"] == "latin"
    assert gt["page_text"] == "Hello world"


def test_build_gt_export_reconstructs_page_text_when_missing(ann_minimal_dict):
    ann_minimal_dict["gt_page_text"] = ""
    ann_minimal_dict["lines"].append(
        {
            "line_id": 1,
            "block_id": 0,
            "line_type": "text",
            "line_order_in_block": 1,
            "global_line_order": 1,
            "bbox": [10, 40, 60, 20],
            "gt_text": "Second line",
            "gt_script": "latin",
        }
    )

    gt = _build_gt_export(ann_minimal_dict)

    assert gt["page_text"] == "Hello world\nSecond line"


def test_build_gt_export_keeps_latex_field(ann_math_dict):
    gt = _build_gt_export(ann_math_dict)

    assert gt["lines"][0]["line_type"] == "math"
    assert gt["lines"][0]["latex"] == r"x^2 + y^2 = z^2"
    assert gt["meta"]["has_equation"] is True


# ======================================================================================
# split helpers
# ======================================================================================

def test_normalized_split_ratios_normalizes_sum():
    run_cfg = {"splits": {"train": 8, "val": 1, "test": 1}}

    tr, va, te = _normalized_split_ratios(run_cfg)

    assert round(tr, 6) == 0.8
    assert round(va, 6) == 0.1
    assert round(te, 6) == 0.1
    assert round(tr + va + te, 6) == 1.0


def test_normalized_split_ratios_uses_defaults_when_sum_is_zero():
    run_cfg = {"splits": {"train": 0, "val": 0, "test": 0}}

    tr, va, te = _normalized_split_ratios(run_cfg)

    assert (tr, va, te) == (0.80, 0.10, 0.10)


def test_split_of_assigns_train_val_test_ranges():
    run_cfg = {"splits": {"train": 0.6, "val": 0.2, "test": 0.2}}

    assert _split_of(0, 10, run_cfg) == "train"
    assert _split_of(5, 10, run_cfg) == "train"
    assert _split_of(6, 10, run_cfg) == "val"
    assert _split_of(7, 10, run_cfg) == "val"
    assert _split_of(8, 10, run_cfg) == "test"
    assert _split_of(9, 10, run_cfg) == "test"



