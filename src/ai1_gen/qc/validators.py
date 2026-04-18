# src/ai1_gen/qc/validators.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

from typing import Any, Dict, Tuple, Optional, List
import numpy as np


def _is_binary_u8(mask: np.ndarray) -> bool:
    if mask.dtype != np.uint8:
        return False
    return bool(np.all((mask == 0) | (mask == 255)))


def _clamp_bbox_xywh(x: int, y: int, w: int, h: int, W: int, H: int) -> Tuple[int, int, int, int]:
    x0 = max(0, min(W - 1, int(x)))
    y0 = max(0, min(H - 1, int(y)))
    x1 = max(0, min(W, x0 + max(1, int(w))))
    y1 = max(0, min(H, y0 + max(1, int(h))))
    if x1 <= x0:
        x1 = min(W, x0 + 1)
    if y1 <= y0:
        y1 = min(H, y0 + 1)
    return x0, y0, x1, y1


def _xywh_to_xyxy(b: List[int] | Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    x, y, w, h = map(int, b)
    return int(x), int(y), int(x + max(1, w)), int(y + max(1, h))


def _bbox_area_xywh(b: List[int] | Tuple[int, int, int, int]) -> int:
    _, _, w, h = map(int, b)
    return max(0, w) * max(0, h)


def _inter_area_xyxy(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> int:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0
    return (ix1 - ix0) * (iy1 - iy0)


def _eligible_mask_from_ann(
    ann: Dict[str, Any],
    H: int,
    W: int,
    *,
    exclude_block_types: Tuple[str, ...] = ("auto_figure", "figure"),
    pad_px: int = 6,
) -> np.ndarray:
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
            x0, y0, x1, y1 = _clamp_bbox_xywh(int(bx), int(by), int(bw), int(bh), W, H)

            x0 = max(0, x0 - pad_px)
            y0 = max(0, y0 - pad_px)
            x1 = min(W, x1 + pad_px)
            y1 = min(H, y1 + pad_px)

            eligible[y0:y1, x0:x1] = False
        except Exception:
            continue

    return eligible


def compute_density_metrics(mask_text: np.ndarray, mask_math: np.ndarray, ann: Dict[str, Any], cfg) -> Dict[str, Any]:
    H, W = int(mask_text.shape[0]), int(mask_text.shape[1])
    total_px = float(max(1, H * W))

    qc_cfg = cfg.qc()
    dens_cfg = (qc_cfg.get("density") or {}) if isinstance(qc_cfg, dict) else {}

    use_eligible = bool(dens_cfg.get("use_eligible_area_excluding_figures", True))
    eligible_pad = int(dens_cfg.get("eligible_pad_px", 6))
    exclude_types = tuple(dens_cfg.get("exclude_block_types", ["auto_figure", "figure"]))

    if use_eligible:
        eligible = _eligible_mask_from_ann(ann, H, W, exclude_block_types=exclude_types, pad_px=eligible_pad)
        eligible_px = float(max(1, int(np.count_nonzero(eligible))))
    else:
        eligible = None
        eligible_px = total_px

    t = (mask_text > 0)
    m = (mask_math > 0)
    c = (t | m)

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


def mixed_band_variance(mask_bool: np.ndarray, bands: int, eligible: Optional[np.ndarray] = None) -> float:
    H = int(mask_bool.shape[0])
    bands = max(2, int(bands))
    bs = max(1, H // bands)

    ratios: List[float] = []
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

    floors = dens_cfg.get("lo_floor_by_density", {
        "sparse": 0.0008,
        "normal": 0.0150,
        "dense": 0.0600,
        "mixed": 0.0120,
    })
    floor = float(floors.get(density_level, floors.get("normal", 0.0150)))
    lo_adj = max(floor, lo_adj)

    hi_adj = min(1.0, max(lo_adj + 1e-6, hi_adj))

    return lo_adj, hi_adj, {"scales": scales_applied, "lo_floor": floor}


def _soft_in_range(x: float, lo: float, hi: float, margin_abs: float) -> bool:
    lo2 = max(0.0, lo - margin_abs)
    hi2 = min(1.0, hi + margin_abs)
    return bool(lo2 <= x <= hi2)


def _best_density_bucket(x: float, ranges: Dict[str, Any], margin_abs: float) -> Optional[str]:
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


def _collect_blocks_by_type(ann: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for b in ann.get("blocks", []) or []:
        bt = str(b.get("block_type", ""))
        out.setdefault(bt, []).append(b)
    return out


def _validate_block_overlaps(
    ann: Dict[str, Any],
    max_iou_like: float = 0.35,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    blocks = ann.get("blocks", []) or []
    n = len(blocks)
    for i in range(n):
        bi = blocks[i]
        ti = str(bi.get("block_type", ""))
        if ti in {"caption"}:
            continue

        box_i_xywh = bi.get("bbox", [0, 0, 0, 0])
        ai = float(max(1, _bbox_area_xywh(box_i_xywh)))
        box_i = _xywh_to_xyxy(box_i_xywh)

        for j in range(i + 1, n):
            bj = blocks[j]
            tj = str(bj.get("block_type", ""))
            if tj in {"caption"}:
                continue

            box_j_xywh = bj.get("bbox", [0, 0, 0, 0])
            aj = float(max(1, _bbox_area_xywh(box_j_xywh)))
            box_j = _xywh_to_xyxy(box_j_xywh)

            inter = float(_inter_area_xyxy(box_i, box_j))
            if inter <= 0:
                continue

            ratio = inter / min(ai, aj)
            if ratio > max_iou_like:
                return False, {
                    "block_a_id": bi.get("block_id"),
                    "block_b_id": bj.get("block_id"),
                    "overlap_ratio_min_area": ratio,
                    "block_a_type": ti,
                    "block_b_type": tj,
                }

    return True, None


def _validate_title_position(ann: Dict[str, Any], H: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
    titles = [b for b in ann.get("blocks", []) or [] if str(b.get("block_type", "")) == "title"]
    if not titles:
        return True, None

    top_limit = 0.28 * float(H)
    for t in titles:
        _, y, _, _ = t.get("bbox", [0, 0, 0, 0])
        if float(y) > top_limit:
            return False, {
                "title_block_id": t.get("block_id"),
                "title_y": float(y),
                "top_limit": float(top_limit),
            }
    return True, None


def _validate_caption_proximity(ann: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    blocks = ann.get("blocks", []) or []
    figs_tbls = [
        b for b in blocks
        if str(b.get("block_type", "")) in {"figure", "auto_figure", "table", "auto_table"}
    ]
    captions = [b for b in blocks if str(b.get("block_type", "")) == "caption"]

    if not captions:
        return True, None

    if not figs_tbls:
        return False, {"reason": "caption-exists-without-figure-or-table"}

    for cap in captions:
        cx, cy, cw, ch = map(int, cap.get("bbox", [0, 0, 0, 0]))
        cap_center_x = cx + cw / 2.0
        cap_center_y = cy + ch / 2.0

        best = None
        for fb in figs_tbls:
            fx, fy, fw, fh = map(int, fb.get("bbox", [0, 0, 0, 0]))
            fig_center_x = fx + fw / 2.0
            fig_center_y = fy + fh / 2.0
            dist = ((cap_center_x - fig_center_x) ** 2 + (cap_center_y - fig_center_y) ** 2) ** 0.5
            if best is None or dist < best[0]:
                best = (dist, fb)

        if best is None:
            continue

        dist, fb = best
        fx, fy, fw, fh = map(int, fb.get("bbox", [0, 0, 0, 0]))
        allowed = max(fh * 1.35, ch * 8.0, 80.0)
        if dist > allowed:
            return False, {
                "caption_block_id": cap.get("block_id"),
                "nearest_block_id": fb.get("block_id"),
                "distance": float(dist),
                "allowed": float(allowed),
            }

    return True, None


def _validate_line_boxes(ann: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    lines = ann.get("lines", []) or []
    for ln in lines:
        x, y, w, h = map(int, ln.get("bbox", [0, 0, 0, 0]))
        if w < 4 or h < 4:
            return False, {
                "line_id": ln.get("line_id"),
                "bbox": [x, y, w, h],
                "reason": "too-small-line-bbox",
            }
    return True, None


def _validate_reading_order_soft(ann: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    lines = sorted(ann.get("lines", []) or [], key=lambda z: int(z.get("global_line_order", 0)))
    if len(lines) < 2:
        return True, None

    backward_jumps = 0
    prev_y = None
    for ln in lines:
        y = int((ln.get("bbox", [0, 0, 0, 0]) or [0, 0, 0, 0])[1])
        if prev_y is not None and y + 12 < prev_y:
            backward_jumps += 1
        prev_y = y

    limit = 0 if len(lines) < 4 else max(4, len(lines) // 6)
    if backward_jumps > limit:
        return False, {
            "backward_jumps": int(backward_jumps),
            "line_count": int(len(lines)),
        }

    return True, None

def _validate_page_family_rules(ann: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    meta = ann.get("meta", {}) or {}

    if bool(meta.get("_fallback", False)):
        return True, None

    page_family = str(meta.get("page_family", "report"))
    blocks_by_type = _collect_blocks_by_type(ann)

    if page_family in {"academic", "book", "report", "worksheet", "notes"}:
        if not blocks_by_type.get("title"):
            return False, {"page_family": page_family, "reason": "missing-title"}

    if page_family == "academic":
        has_body = bool(blocks_by_type.get("paragraph")) or bool(blocks_by_type.get("list"))
        if not has_body:
            return False, {"page_family": page_family, "reason": "missing-body"}

    return True, None


def validate_page(
    ann: Dict[str, Any],
    mask_text: np.ndarray,
    mask_math: np.ndarray,
    cfg
) -> Tuple[bool, str | None, Dict[str, Any]]:
    qc_cfg = cfg.qc()
    thr = cfg.thresholds()

    # 1) Mask Binary
    if bool(qc_cfg.get("mask_binary_required", True)):
        if not _is_binary_u8(mask_text) or not _is_binary_u8(mask_math):
            return False, "qc/mask-not-binary", {}

    # 2) overlap
    overlap = np.logical_and(mask_text > 0, mask_math > 0)
    text_pixels = max(1, int(np.sum(mask_text > 0)))
    overlap_ratio = float(np.sum(overlap)) / float(text_pixels)
    if overlap_ratio >= float(qc_cfg.get("overlap_text_over_math_max_ratio", 0.01)):
        return False, "qc/overlap-too-high", {"overlap_ratio": overlap_ratio}

    # 3) global line order
    if bool(qc_cfg.get("require_global_line_order_contiguous", True)):
        lines = ann.get("lines", [])
        for i, ln in enumerate(lines):
            if int(ln.get("global_line_order", -1)) != i:
                return False, "qc/order-not-contiguous", {"expected": i, "found": ln.get("global_line_order")}

    meta = ann.get("meta", {}) or {}
    density_level = str(meta.get("density_level", "normal"))
    H, W = int(mask_text.shape[0]), int(mask_text.shape[1])

    # 3.5) line bbox sanity
    good_lines, extra_lines = _validate_line_boxes(ann)
    if not good_lines:
        return False, "qc/invalid-line-bbox", extra_lines or {}

    # 3.6) block overlap sanity
    good_blocks, extra_blocks = _validate_block_overlaps(
        ann,
        max_iou_like=float(qc_cfg.get("max_block_overlap_ratio_min_area", 0.35)),
    )
    if not good_blocks:
        return False, "qc/block-overlap-too-high", extra_blocks or {}

    # 3.7) title upper-region sanity
    if bool(qc_cfg.get("require_title_near_top", True)):
        good_title, extra_title = _validate_title_position(ann, H)
        if not good_title:
            return False, "qc/title-too-low", extra_title or {}

    # 3.8) caption proximity sanity
    if bool(qc_cfg.get("require_caption_near_target", True)):
        good_cap, extra_cap = _validate_caption_proximity(ann)
        if not good_cap:
            return False, "qc/caption-placement-invalid", extra_cap or {}

    # 3.9) page-family sanity
    if bool(qc_cfg.get("use_page_family_rules", True)):
        good_family, extra_family = _validate_page_family_rules(ann)
        if not good_family:
            return False, "qc/page-family-rule-failed", extra_family or {}

    # 3.10) reading order soft sanity
    if bool(qc_cfg.get("soft_reading_order_check", True)):
        good_ro, extra_ro = _validate_reading_order_soft(ann)
        if not good_ro:
            return False, "qc/reading-order-suspicious", extra_ro or {}

    # ---- Density metrics
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

    # 4) Density range check
    ranges = thr.get("ink_ratio_text_ranges", {}) or {}
    if density_level in ranges:
        base_lo, base_hi = ranges[density_level]
        base_lo = float(base_lo)
        base_hi = float(base_hi)

        lo_adj, hi_adj, adj_info = _apply_density_adjustments(density_level, base_lo, base_hi, meta, m, cfg)

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

    # 5) Mixed variance
    if str(meta.get("density_level", density_level)) == "mixed":
        mb = thr.get("mixed", {}) or {}
        bands = int(mb.get("bands", 8))
        vthr = float(mb.get("variance_thr", 0.00010))

        use_eligible = bool(qc_density_cfg.get("use_eligible_area_excluding_figures", True))
        eligible = _eligible_mask_from_ann(
            ann, H, W,
            exclude_block_types=tuple(qc_density_cfg.get("exclude_block_types", ["auto_figure", "figure"])),
            pad_px=int(qc_density_cfg.get("eligible_pad_px", 6)),
        ) if use_eligible else None

        content_bool = (mask_text > 0) | (mask_math > 0)
        v = mixed_band_variance(content_bool, bands=bands, eligible=eligible)

        var_soft_scale = float(qc_density_cfg.get("mixed_variance_soft_scale", 0.85))
        if v <= vthr and v < (vthr * var_soft_scale):
            return False, "qc/mixed-variance-too-low", {"var": float(v), "thr": float(vthr)}

    # 6) Scale profile & DPI match
    scale_profile = str(meta.get("scale_profile", "dpi300"))
    dpi = int(ann.get("size", {}).get("dpi", 300))
    if scale_profile == "dpi200" and dpi != 200:
        return False, "qc/scale-profile-mismatch", {"scale_profile": scale_profile, "dpi": dpi}
    if scale_profile == "dpi300" and dpi != 300:
        return False, "qc/scale-profile-mismatch", {"scale_profile": scale_profile, "dpi": dpi}

    return True, None, {
        "overlap_ratio": overlap_ratio,
        **m,
        "page_family": meta.get("page_family", "report"),
    }