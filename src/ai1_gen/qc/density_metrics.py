# src/ai1_gen/qc/density_metrics.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np

from .bbox_utils import _clamp_bbox_xywh


def _eligible_mask_from_ann(
    ann: Dict[str, Any],
    H: int,
    W: int,
    *,
    exclude_block_types: Tuple[str, ...] = ("auto_figure", "figure"),
    pad_px: int = 6,
) -> np.ndarray:
    """
    Build a boolean mask for areas eligible for density calculation.

    Figure-like blocks can be excluded so that large non-text regions do not
    incorrectly make text density look too low.
    """
    eligible = np.ones((H, W), dtype=bool)
    blocks = ann.get("blocks", []) or []

    if not blocks:
        return eligible

    for b in blocks:
        try:
            btype = str(b.get("block_type", ""))

            if btype not in exclude_block_types:
                continue

            bx, by, bw, bh = b.get("bbox", [0, 0, 0, 0])
            x0, y0, x1, y1 = _clamp_bbox_xywh(
                int(bx),
                int(by),
                int(bw),
                int(bh),
                W,
                H,
            )

            x0 = max(0, x0 - pad_px)
            y0 = max(0, y0 - pad_px)
            x1 = min(W, x1 + pad_px)
            y1 = min(H, y1 + pad_px)

            eligible[y0:y1, x0:x1] = False

        except Exception:
            continue

    return eligible


def compute_density_metrics(
    mask_text: np.ndarray,
    mask_math: np.ndarray,
    ann: Dict[str, Any],
    cfg,
) -> Dict[str, Any]:
    """Compute global and eligible-area ink density metrics."""
    H, W = int(mask_text.shape[0]), int(mask_text.shape[1])
    total_px = float(max(1, H * W))

    qc_cfg = cfg.qc()
    dens_cfg = (qc_cfg.get("density") or {}) if isinstance(qc_cfg, dict) else {}

    use_eligible = bool(dens_cfg.get("use_eligible_area_excluding_figures", True))
    eligible_pad = int(dens_cfg.get("eligible_pad_px", 6))
    exclude_types = tuple(dens_cfg.get("exclude_block_types", ["auto_figure", "figure"]))

    if use_eligible:
        eligible = _eligible_mask_from_ann(
            ann,
            H,
            W,
            exclude_block_types=exclude_types,
            pad_px=eligible_pad,
        )
        eligible_px = float(max(1, int(np.count_nonzero(eligible))))
    else:
        eligible = None
        eligible_px = total_px

    t = mask_text > 0
    m = mask_math > 0
    c = t | m

    ink_text_global = float(np.count_nonzero(t)) / total_px
    ink_math_global = float(np.count_nonzero(m)) / total_px
    ink_content_global = float(np.count_nonzero(c)) / total_px

    if eligible is not None:
        ink_text_elig = float(np.count_nonzero(t & eligible)) / eligible_px
        ink_math_elig = float(np.count_nonzero(m & eligible)) / eligible_px
        ink_content_elig = float(np.count_nonzero(c & eligible)) / eligible_px
        excluded_frac = 1.0 - (eligible_px / total_px)
    else:
        ink_text_elig = ink_text_global
        ink_math_elig = ink_math_global
        ink_content_elig = ink_content_global
        excluded_frac = 0.0

    return {
        "ink_ratio_text": ink_text_global,
        "ink_ratio_math": ink_math_global,
        "ink_ratio_content": ink_content_global,
        "ink_ratio_text_eligible": ink_text_elig,
        "ink_ratio_math_eligible": ink_math_elig,
        "ink_ratio_content_eligible": ink_content_elig,
        "eligible_excluded_frac": float(excluded_frac),
    }


def mixed_band_variance(
    mask_bool: np.ndarray,
    bands: int,
    eligible: Optional[np.ndarray] = None,
) -> float:
    """Compute vertical-band variance for mixed-density pages."""
    H = int(mask_bool.shape[0])
    bands = max(2, int(bands))
    bs = max(1, H // bands)

    ratios: list[float] = []

    for i in range(bands):
        y0 = i * bs
        y1 = H if i == bands - 1 else (i + 1) * bs

        band_mask = mask_bool[y0:y1, :]

        if eligible is not None:
            band_elig = eligible[y0:y1, :]
            denom = float(max(1, int(np.count_nonzero(band_elig))))
            num = float(np.count_nonzero(band_mask & band_elig))
            ratios.append(num / denom)
        else:
            ratios.append(float(np.mean(band_mask)))

    return float(np.var(np.array(ratios, dtype=np.float32)))


def _apply_density_adjustments(
    density_level: str,
    lo: float,
    hi: float,
    meta: Dict[str, Any],
    metrics: Dict[str, Any],
    cfg,
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Adjust density lower/upper bounds for page content composition.

    Large figures, tables, and equations can lower apparent text density.
    This adjustment avoids rejecting valid pages too aggressively.
    """
    qc_cfg = cfg.qc()
    dens_cfg = (qc_cfg.get("density") or {}) if isinstance(qc_cfg, dict) else {}

    has_fig = bool(meta.get("has_figure", False))
    has_tbl = bool(meta.get("has_table", False))
    has_eq = bool(meta.get("has_equation", False))

    fig_lo_scale = float(dens_cfg.get("figure_lo_scale", 0.75))
    tbl_lo_scale = float(dens_cfg.get("table_lo_scale", 0.85))
    eq_lo_scale = float(dens_cfg.get("equation_lo_scale", 0.85))

    excluded_frac = float(metrics.get("eligible_excluded_frac", 0.0))
    excluded_lo_scale = float(dens_cfg.get("excluded_area_lo_scale", 0.80))
    dynamic_excluded_scale = max(0.55, 1.0 - excluded_lo_scale * excluded_frac)

    lo_adj = float(lo)
    hi_adj = float(hi)

    scales_applied: Dict[str, float] = {"excluded": dynamic_excluded_scale}

    lo_adj *= dynamic_excluded_scale

    if has_fig:
        lo_adj *= fig_lo_scale
        scales_applied["figure"] = fig_lo_scale

    if has_tbl:
        lo_adj *= tbl_lo_scale
        scales_applied["table"] = tbl_lo_scale

    if has_eq:
        lo_adj *= eq_lo_scale
        scales_applied["equation"] = eq_lo_scale

    floors = dens_cfg.get(
        "lo_floor_by_density",
        {
            "sparse": 0.0008,
            "normal": 0.0150,
            "dense": 0.0600,
            "mixed": 0.0120,
        },
    )

    floor = float(floors.get(density_level, floors.get("normal", 0.0150)))
    lo_adj = max(floor, lo_adj)
    hi_adj = min(1.0, max(lo_adj + 1e-6, hi_adj))

    return lo_adj, hi_adj, {"scales": scales_applied, "lo_floor": floor}


def _soft_in_range(
    x: float,
    lo: float,
    hi: float,
    margin_abs: float,
) -> bool:
    """Return True if x is inside [lo, hi] with an absolute soft margin."""
    lo2 = max(0.0, lo - margin_abs)
    hi2 = min(1.0, hi + margin_abs)

    return bool(lo2 <= x <= hi2)


def _best_density_bucket(
    x: float,
    ranges: Dict[str, Any],
    margin_abs: float,
) -> Optional[str]:
    """Find the closest density bucket that accepts x within a soft margin."""
    cands = []

    for k, v in ranges.items():
        try:
            lo, hi = float(v[0]), float(v[1])

            if _soft_in_range(x, lo, hi, margin_abs):
                center = 0.5 * (lo + hi)
                cands.append((abs(x - center), str(k)))

        except Exception:
            continue

    if not cands:
        return None

    cands.sort(key=lambda t: t[0])
    return cands[0][1]