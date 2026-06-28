# src/docsynthfab/qc/validators.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np

from .bbox_utils import _bbox_union_extent_ratio_from_ann
from .content_contracts import (
    _validate_content_purity_contract,
    _validate_text_no_code_token_leakage,
    _validate_text_no_tofu_chars,
)
from .density_metrics import (
    _apply_density_adjustments,
    _best_density_bucket,
    _eligible_mask_from_ann,
    _soft_in_range,
    compute_density_metrics,
    mixed_band_variance,
)
from .layout_rules import (
    _validate_block_overlaps,
    _validate_caption_proximity,
    _validate_line_boxes,
    _validate_page_family_rules,
    _validate_reading_order_soft,
    _validate_title_position,
)
from .mask_checks import _is_binary_u8, _visual_content_ratio
from .visual_quality import _minimum_visual_quality_thresholds


def _bbox_inside_page(bbox, page_w: int, page_h: int) -> bool:
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False

    try:
        x, y, w, h = [float(v) for v in bbox]
    except Exception:
        return False

    if w <= 0 or h <= 0:
        return False

    if x < 0 or y < 0:
        return False

    if x >= page_w or y >= page_h:
        return False

    if x + w > page_w or y + h > page_h:
        return False

    return True


def _validate_bboxes_inside_page(ann: dict):
    size = ann.get("size") or {}

    try:
        page_w = int(size.get("w"))
        page_h = int(size.get("h"))
    except Exception:
        return False, "qc/invalid-page-size", {"size": size}

    if page_w <= 0 or page_h <= 0:
        return False, "qc/invalid-page-size", {"size": size}

    for kind in ("blocks", "lines"):
        items = ann.get(kind, [])

        if not isinstance(items, list):
            return False, "qc/invalid-annotation-list", {"kind": kind}

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                return False, "qc/invalid-annotation-item", {
                    "kind": kind,
                    "index": index,
                }

            bbox = item.get("bbox")

            if not _bbox_inside_page(bbox, page_w, page_h):
                return False, "qc/bbox-outside-page", {
                    "kind": kind,
                    "index": index,
                    "bbox": bbox,
                    "page_w": page_w,
                    "page_h": page_h,
                }

    return True, None, {}


def validate_page(
    ann: Dict[str, Any],
    mask_text: np.ndarray,
    mask_math: np.ndarray,
    cfg,
) -> Tuple[bool, str | None, Dict[str, Any]]:
    """
    Validate a generated page annotation and its text/math masks.

    Returns:
        (ok, error_code, extra)

    Contract:
    - Does not mutate data except for allowed density-level remapping.
    - Rejects invalid masks, excessive overlaps, broken layout contracts,
      density mismatches, and suspicious visual coverage.
    """
    qc_cfg = cfg.qc()
    thr = cfg.thresholds()

    # 1) Mask binary check.
    if bool(qc_cfg.get("mask_binary_required", True)):
        if not _is_binary_u8(mask_text) or not _is_binary_u8(mask_math):
            return False, "qc/mask-not-binary", {}

    # 2) Text/math overlap check.
    overlap = np.logical_and(mask_text > 0, mask_math > 0)
    text_pixels = max(1, int(np.sum(mask_text > 0)))
    overlap_ratio = float(np.sum(overlap)) / float(text_pixels)

    if overlap_ratio >= float(qc_cfg.get("overlap_text_over_math_max_ratio", 0.01)):
        return False, "qc/overlap-too-high", {
            "overlap_ratio": overlap_ratio,
        }

    # 3) Global line order contiguity.
    if bool(qc_cfg.get("require_global_line_order_contiguous", True)):
        lines = ann.get("lines", [])

        for i, ln in enumerate(lines):
            if int(ln.get("global_line_order", -1)) != i:
                return False, "qc/order-not-contiguous", {
                    "expected": i,
                    "found": ln.get("global_line_order"),
                }

    meta = ann.get("meta", {}) or {}
    density_level = str(meta.get("density_level", "normal"))
    H, W = int(mask_text.shape[0]), int(mask_text.shape[1])

    ok, code, extra = _validate_bboxes_inside_page(ann)
    if not ok:
        return False, code, extra


    # 3.1) Content purity contract.
    # This catches table=100 / latex=100 / text=100 leaks.
    if bool(qc_cfg.get("require_content_purity_contract", True)):
        good_purity, extra_purity = _validate_content_purity_contract(ann, cfg)

        if not good_purity:
            return False, "qc/content-purity-violated", extra_purity or {}

    # 3.2) Text glyph/tofu guard.
    if bool(qc_cfg.get("reject_tofu_text_chars", True)):
        good_tofu, extra_tofu = _validate_text_no_tofu_chars(ann)

        if not good_tofu:
            return False, "qc/text-tofu-char-detected", extra_tofu or {}

    # 3.2b) Synthetic code/noisy token leakage guard.
    if bool(qc_cfg.get("reject_code_token_leakage", True)):
        good_code_tokens, extra_code_tokens = _validate_text_no_code_token_leakage(
            ann,
            max_leak_count=int(qc_cfg.get("max_code_token_leak_count", 0)),
        )

        if not good_code_tokens:
            return False, "qc/code-token-leakage-detected", extra_code_tokens or {}

    # 3.3) Minimum visual coverage / tiny-page guard.
    min_content_ratio, min_bbox_extent_ratio = _minimum_visual_quality_thresholds(
        density_level=density_level,
        meta=meta,
        qc_cfg=qc_cfg,
    )

    if min_content_ratio > 0.0 or min_bbox_extent_ratio > 0.0:
        content_ratio = _visual_content_ratio(mask_text, mask_math)
        bbox_extent_ratio = _bbox_union_extent_ratio_from_ann(ann, W, H)

        if content_ratio < min_content_ratio and bbox_extent_ratio < min_bbox_extent_ratio:
            return False, "qc/visual-coverage-too-low", {
                "content_ratio": float(content_ratio),
                "min_content_ratio": float(min_content_ratio),
                "bbox_extent_ratio": float(bbox_extent_ratio),
                "min_bbox_extent_ratio": float(min_bbox_extent_ratio),
                "density_level": density_level,
                "has_equation_layout": bool(meta.get("has_equation_layout", False)),
                "has_equation": bool(meta.get("has_equation", False)),
                "has_table": bool(meta.get("has_table", False)),
            }

    # 3.4) Line bbox sanity.
    good_lines, extra_lines = _validate_line_boxes(ann)

    if not good_lines:
        return False, "qc/invalid-line-bbox", extra_lines or {}

    # 3.5) Block overlap sanity.
    good_blocks, extra_blocks = _validate_block_overlaps(
        ann,
        max_iou_like=float(qc_cfg.get("max_block_overlap_ratio_min_area", 0.35)),
    )

    if not good_blocks:
        return False, "qc/block-overlap-too-high", extra_blocks or {}

    # 3.6) Title upper-region sanity.
    if bool(qc_cfg.get("require_title_near_top", True)):
        good_title, extra_title = _validate_title_position(ann, H)

        if not good_title:
            return False, "qc/title-too-low", extra_title or {}

    # 3.7) Caption proximity sanity.
    if bool(qc_cfg.get("require_caption_near_target", True)):
        good_cap, extra_cap = _validate_caption_proximity(ann)

        if not good_cap:
            return False, "qc/caption-placement-invalid", extra_cap or {}

    # 3.8) Page-family sanity.
    if bool(qc_cfg.get("use_page_family_rules", True)):
        good_family, extra_family = _validate_page_family_rules(ann)

        if not good_family:
            return False, "qc/page-family-rule-failed", extra_family or {}

    # 3.9) Reading-order soft sanity.
    if bool(qc_cfg.get("soft_reading_order_check", True)):
        good_ro, extra_ro = _validate_reading_order_soft(ann)

        if not good_ro:
            return False, "qc/reading-order-suspicious", extra_ro or {}

    # 4) Density metrics.
    m = compute_density_metrics(mask_text, mask_math, ann, cfg)

    qc_density_cfg = (qc_cfg.get("density") or {}) if isinstance(qc_cfg, dict) else {}

    use_content_if_equation = bool(qc_density_cfg.get("use_content_union_if_equation", True))
    margin_abs = float(qc_density_cfg.get("density_soft_margin_abs", 0.0025))
    allow_remap = bool(qc_density_cfg.get("allow_density_remap", True))

    has_eq = bool(meta.get("has_equation", False))

    if use_content_if_equation and has_eq:
        ink = float(m["ink_ratio_content_eligible"])
        ink_kind = "content_eligible"
    else:
        ink = float(m["ink_ratio_text_eligible"])
        ink_kind = "text_eligible"

    # 5) Density range check.
    ranges = thr.get("ink_ratio_text_ranges", {}) or {}

    if density_level in ranges:
        base_lo, base_hi = ranges[density_level]
        base_lo = float(base_lo)
        base_hi = float(base_hi)

        lo_adj, hi_adj, adj_info = _apply_density_adjustments(
            density_level,
            base_lo,
            base_hi,
            meta,
            m,
            cfg,
        )

        if not _soft_in_range(ink, lo_adj, hi_adj, margin_abs):
            if allow_remap:
                new_level = _best_density_bucket(ink, ranges, margin_abs)

                if new_level is not None and new_level != density_level:
                    meta["density_level"] = new_level

                    try:
                        ann["meta"]["density_level"] = new_level
                    except Exception:
                        pass

                    return True, None, {
                        "overlap_ratio": overlap_ratio,
                        **m,
                        "density_used": ink_kind,
                        "density_value": float(ink),
                        "density_expected": [float(lo_adj), float(hi_adj)],
                        "density_base_expected": [float(base_lo), float(base_hi)],
                        "density_adjust": adj_info,
                        "density_remap_from": density_level,
                        "density_remap_to": new_level,
                        "density_soft_margin_abs": float(margin_abs),
                    }

            return False, "qc/density-out-of-range", {
                "ink_ratio_text": float(m["ink_ratio_text"]),
                "ink_ratio_text_eligible": float(m["ink_ratio_text_eligible"]),
                "ink_ratio_math": float(m["ink_ratio_math"]),
                "ink_ratio_content_eligible": float(m["ink_ratio_content_eligible"]),
                "density_used": ink_kind,
                "density_value": float(ink),
                "expected": [float(lo_adj), float(hi_adj)],
                "base_expected": [float(base_lo), float(base_hi)],
                "density_adjust": adj_info,
                "density_soft_margin_abs": float(margin_abs),
            }

    # 6) Mixed density variance check.
    if str(meta.get("density_level", density_level)) == "mixed":
        mb = thr.get("mixed", {}) or {}
        bands = int(mb.get("bands", 8))
        vthr = float(mb.get("variance_thr", 0.00010))

        use_eligible = bool(qc_density_cfg.get("use_eligible_area_excluding_figures", True))

        eligible = (
            _eligible_mask_from_ann(
                ann,
                H,
                W,
                exclude_block_types=tuple(
                    qc_density_cfg.get("exclude_block_types", ["auto_figure", "figure"])
                ),
                pad_px=int(qc_density_cfg.get("eligible_pad_px", 6)),
            )
            if use_eligible
            else None
        )

        content_bool = (mask_text > 0) | (mask_math > 0)
        v = mixed_band_variance(content_bool, bands=bands, eligible=eligible)

        var_soft_scale = float(qc_density_cfg.get("mixed_variance_soft_scale", 0.85))

        if v <= vthr and v < (vthr * var_soft_scale):
            return False, "qc/mixed-variance-too-low", {
                "var": float(v),
                "thr": float(vthr),
            }

    # 7) Scale profile and DPI match.
    scale_profile = str(meta.get("scale_profile", "dpi300"))
    dpi = int(ann.get("size", {}).get("dpi", 300))

    if scale_profile == "dpi200" and dpi != 200:
        return False, "qc/scale-profile-mismatch", {
            "scale_profile": scale_profile,
            "dpi": dpi,
        }

    if scale_profile == "dpi300" and dpi != 300:
        return False, "qc/scale-profile-mismatch", {
            "scale_profile": scale_profile,
            "dpi": dpi,
        }

    return True, None, {
        "overlap_ratio": overlap_ratio,
        **m,
        "page_family": meta.get("page_family", "report"),
    }



