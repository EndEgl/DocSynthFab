# src/docsynthfab/layout/layout_sampler.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import List, Tuple

from .block_mix import (
    make_block_mix_sequence as _make_block_mix_sequence,
    normalize_block_mix as _normalize_block_mix,
)
from .block_placement import assign_block_positions as _assign_block_positions
from .common import (
    choice_dist as _choice_dist,
    page_size_meta as _page_size_meta,
    rand_range as _rand_range,
)
from .line_bboxes import (
    _caption_line_bbox,
    _equation_line_bbox,
    _list_line_bbox,
    _paragraph_line_bbox,
    _title_line_bbox,
)
from .line_gap import _apply_line_gap_randomness, resolve_line_gap_policy
from .line_metrics import _line_height_px, _line_type_of_block, _max_lines_in_block
from .line_planning import _initial_line_plan
from .line_rebalance import _rebalance_line_counts
from .occupancy import (
    refine_block_positions_with_occupancy as _refine_block_positions_with_occupancy,
)
from .page_traits import (
    sample_layout_type as _sample_layout_type,
    sample_page_family as _sample_page_family,
    sample_page_size as _sample_page_size,
)
from .specs import BlockSpec, LineSpec, PageSpec



from .table_cell_bboxes import _table_cell_bboxes

def _overlap_ratio_min_area_xywh(a, b) -> float:
    ax, ay, aw, ah = [int(v) for v in a]
    bx, by, bw, bh = [int(v) for v in b]

    ax1 = ax + max(0, aw)
    ay1 = ay + max(0, ah)
    bx1 = bx + max(0, bw)
    by1 = by + max(0, bh)

    ix0 = max(ax, bx)
    iy0 = max(ay, by)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)

    iw = max(0, ix1 - ix0)
    ih = max(0, iy1 - iy0)
    inter = iw * ih

    if inter <= 0:
        return 0.0

    area_a = max(1, aw * ah)
    area_b = max(1, bw * bh)

    return float(inter) / float(min(area_a, area_b))


def _box_too_close_or_overlapping(candidate, accepted, *, max_overlap_ratio: float, min_gap_px: int) -> bool:
    cx, cy, cw, ch = [int(v) for v in candidate]

    padded = (
        cx - int(min_gap_px),
        cy - int(min_gap_px),
        cw + int(min_gap_px) * 2,
        ch + int(min_gap_px) * 2,
    )

    for other in accepted:
        if _overlap_ratio_min_area_xywh(candidate, other) > float(max_overlap_ratio):
            return True

        if _overlap_ratio_min_area_xywh(padded, other) > 0.0:
            return True

    return False


def _clamp_block_xy(x: int, y: int, bw: int, bh: int, *, w: int, h: int, margin_x: int, margin_y: int):
    max_x = max(margin_x, int(w) - int(margin_x) - int(bw))
    max_y = max(margin_y, int(h) - int(margin_y) - int(bh))

    x = max(int(margin_x), min(int(x), int(max_x)))
    y = max(int(margin_y), min(int(y), int(max_y)))

    return int(x), int(y)


def _resolve_block_overlaps_after_occupancy(
    *,
    placed,
    w: int,
    h: int,
    rng,
    layout_cfg,
):
    """
    Final layout safety pass.

    It keeps the existing placement when it is safe.
    If a block overlaps previous accepted blocks, it searches a random free position.
    If no safe position is found, it shrinks the block slightly and retries.
    This prevents qc/block-overlap-too-high fallbacks without weakening QC.
    """

    if not placed:
        return placed

    occ_cfg = {}
    try:
        occ_cfg = (layout_cfg.get("occupancy", {}) or {}) if isinstance(layout_cfg, dict) else {}
    except Exception:
        occ_cfg = {}

    max_attempts = int(occ_cfg.get("final_overlap_resolve_attempts", 160) or 160)
    max_attempts = max(32, min(max_attempts, 400))

    min_gap_px = int(occ_cfg.get("final_min_gap_px", 18) or 18)
    min_gap_px = max(4, min(min_gap_px, 80))

    max_overlap_ratio = float(occ_cfg.get("final_max_overlap_ratio_min_area", 0.08) or 0.08)
    max_overlap_ratio = max(0.0, min(max_overlap_ratio, 0.25))

    margin_x = int(max(32, round(float(w) * 0.055)))
    margin_y = int(max(32, round(float(h) * 0.045)))

    body_x0 = margin_x
    body_y0 = margin_y
    body_x1 = int(w) - margin_x
    body_y1 = int(h) - margin_y
    body_w = max(1, body_x1 - body_x0)
    body_h = max(1, body_y1 - body_y0)

    accepted_boxes = []
    out = []

    def sort_key(item):
        _col, _x, _y, _bw, _bh, block_type, _style = item
        t = str(block_type or "").lower()

        if t == "title":
            pri = 0
        elif t in {"table", "figure", "equation"}:
            pri = 1
        else:
            pri = 2

        return (pri, int(_y), int(_x))

    ordered = sorted(list(enumerate(placed)), key=lambda z: sort_key(z[1]))
    resolved_by_original_idx = {}

    for original_idx, item in ordered:
        col, x, y, bw, bh, block_type, style = item

        col = int(col)
        bw = int(bw)
        bh = int(bh)
        block_type_s = str(block_type or "").lower()

        bw = max(24, min(bw, body_w))
        bh = max(18, min(bh, body_h))

        x, y = _clamp_block_xy(
            int(x),
            int(y),
            bw,
            bh,
            w=w,
            h=h,
            margin_x=margin_x,
            margin_y=margin_y,
        )

        original_candidate = (x, y, bw, bh)

        if not _box_too_close_or_overlapping(
            original_candidate,
            accepted_boxes,
            max_overlap_ratio=max_overlap_ratio,
            min_gap_px=min_gap_px,
        ):
            chosen = original_candidate
        else:
            chosen = None

            for shrink_step in (1.0, 0.92, 0.84, 0.76):
                test_bw = max(24, int(bw * shrink_step))
                test_bh = max(18, int(bh * shrink_step))

                for attempt_i in range(max_attempts):
                    if block_type_s == "title":
                        cand_y_min = body_y0
                        cand_y_max = min(body_y1 - test_bh, body_y0 + int(body_h * 0.18))
                    else:
                        cand_y_min = body_y0
                        cand_y_max = max(body_y0, body_y1 - test_bh)

                    cand_x_min = body_x0
                    cand_x_max = max(body_x0, body_x1 - test_bw)

                    # Önce mevcut x civarını dene, sonra tüm boş alana yay.
                    if attempt_i < max_attempts // 4:
                        jitter_x = int(rng.randint(-body_w // 8, body_w // 8))
                        jitter_y = int(rng.randint(-body_h // 8, body_h // 8))
                        cand_x = int(x) + jitter_x
                        cand_y = int(y) + jitter_y
                    else:
                        cand_x = rng.randint(cand_x_min, cand_x_max) if cand_x_max > cand_x_min else cand_x_min
                        cand_y = rng.randint(cand_y_min, cand_y_max) if cand_y_max > cand_y_min else cand_y_min

                    cand_x, cand_y = _clamp_block_xy(
                        cand_x,
                        cand_y,
                        test_bw,
                        test_bh,
                        w=w,
                        h=h,
                        margin_x=margin_x,
                        margin_y=margin_y,
                    )

                    candidate = (cand_x, cand_y, test_bw, test_bh)

                    if not _box_too_close_or_overlapping(
                        candidate,
                        accepted_boxes,
                        max_overlap_ratio=max_overlap_ratio,
                        min_gap_px=min_gap_px,
                    ):
                        chosen = candidate
                        break

                if chosen is not None:
                    break

            # Son çare: bloğu düşürme, ama en azından sayfa içine sıkıştır.
            # QC yine yakalayabilir; worker retry güvenlik ağı olarak kalır.
            if chosen is None:
                chosen = original_candidate

        accepted_boxes.append(chosen)

        new_x, new_y, new_bw, new_bh = chosen

        new_col = col
        if new_col != -1:
            new_col = 0 if (new_x + new_bw / 2.0) < (float(w) / 2.0) else 1

        resolved_by_original_idx[original_idx] = (
            int(new_col),
            int(new_x),
            int(new_y),
            int(new_bw),
            int(new_bh),
            block_type,
            style,
        )

    for i in range(len(placed)):
        out.append(resolved_by_original_idx.get(i, placed[i]))

    return out


def _target_counts(
    cfg,
    density_level: str,
    page_family: str,
    rng: random.Random,
) -> Tuple[int, int]:
    targets = cfg.density_targets()
    target = targets.get(
        density_level,
        targets.get(
            "normal",
            {
                "line_count_range": (35, 75),
                "block_count_range": (8, 16),
            },
        ),
    )

    line_count = _rand_range(
        rng,
        target["line_count_range"][0],
        target["line_count_range"][1],
    )
    block_count = _rand_range(
        rng,
        target["block_count_range"][0],
        target["block_count_range"][1],
    )

    family_scale = {
        "book": (1.08, 0.95),
        "academic": (1.10, 1.00),
        "report": (0.96, 0.94),
        "worksheet": (0.82, 0.88),
        "notes": (0.72, 0.82),
    }.get(page_family, (1.0, 1.0))

    line_count = max(4, int(round(line_count * family_scale[0])))
    block_count = max(1, int(round(block_count * family_scale[1])))

    if density_level == "mixed":
        line_count = max(line_count, int(line_count * 1.10))

    return line_count, block_count


def sample_page_spec(
    cfg,
    rng: random.Random,
    page_index: int,
    page_id: str,
) -> PageSpec:
    density_level = _choice_dist(rng, cfg.density_dist(), default="normal")
    scale_profile = _choice_dist(rng, cfg.scale_dist(), default="dpi300")
    noise_level = _choice_dist(rng, cfg.noise_dist(), default="medium")

    dpi = 200 if scale_profile == "dpi200" else 300
    page_size_name = _sample_page_size(cfg, rng)
    w, h, page_width_in, page_height_in, orientation = _page_size_meta(
        page_size_name,
        dpi,
    )

    content_cfg = cfg.raw.get("content", {}) or {}
    layout_cfg = cfg.raw.get("layout", {}) or {}
    render_cfg = cfg.raw.get("render", {}) or {}
    non_text_cfg = render_cfg.get("non_text", {}) or {}

    line_gap_policy = resolve_line_gap_policy(layout_cfg)

    table_diversity_scale = float(layout_cfg.get("table_diversity_scale", 0.75))
    table_empty_cell_scale = float(layout_cfg.get("table_empty_cell_scale", 0.35))
    table_merge_cell_scale = float(layout_cfg.get("table_merge_cell_scale", 0.25))
    table_shape_cfg = non_text_cfg.get("table_shape", {}) or {}

    page_family = _sample_page_family(cfg, rng)
    layout_type = _sample_layout_type(cfg, rng, page_family)

    rotation_deg = float(rng.uniform(-2.0, 2.0))
    perspective = bool(rng.random() < 0.25)

    line_count_budget, block_count_budget = _target_counts(
        cfg,
        density_level,
        page_family,
        rng,
    )

    block_mix = _normalize_block_mix(content_cfg)

    seq = _make_block_mix_sequence(
        rng=rng,
        block_budget=block_count_budget,
        block_mix=block_mix,
    )

    placed = _assign_block_positions(
        seq=seq,
        layout_type=layout_type,
        page_family=page_family,
        w=w,
        h=h,
        rng=rng,
        density_level=density_level,
        page_size_name=page_size_name,
    )

    placed = _refine_block_positions_with_occupancy(
        placed=placed,
        w=w,
        h=h,
        density_level=density_level,
        layout_cfg=layout_cfg,
        rng=rng,
    )

    placed = _resolve_block_overlaps_after_occupancy(
        placed=placed,
        w=w,
        h=h,
        rng=rng,
        layout_cfg=layout_cfg,
    )

    blocks: List[BlockSpec] = []

    for block_id, (col, x, y, bw, bh, block_type, style) in enumerate(placed):
        column_id = 0 if col == -1 else col
        style = dict(style)

        if block_type == "table":
            rows = int(style.get("table_rows", 4) or 4)

            min_cell_h = int(style.get("min_table_cell_h", 28) or 28)
            min_table_h = max(96, rows * min_cell_h)

            if int(bh) < min_table_h:
                style["_downgraded_from_table"] = True
                style["_downgrade_reason"] = "table-bbox-too-short"
                style["_original_table_bbox"] = (int(x), int(y), int(bw), int(bh))
                style["_required_min_table_h"] = int(min_table_h)

                block_type = "paragraph"

        blocks.append(
            BlockSpec(
                block_id=block_id,
                block_type=block_type,
                block_order=block_id,
                column_id=column_id,
                bbox=(int(x), int(y), int(bw), int(bh)),
                style=style,
            )
        )

    base_lh = _line_height_px(h, density_level, dpi, page_family, rng)

    mins, desired, caps = _initial_line_plan(
        blocks=blocks,
        base_lh=base_lh,
        page_family=page_family,
        density_level=density_level,
        rng=rng,
        table_diversity_scale=table_diversity_scale,
        table_empty_cell_scale=table_empty_cell_scale,
        table_merge_cell_scale=table_merge_cell_scale,
        table_shape_cfg=table_shape_cfg,
    )

    desired = _rebalance_line_counts(
        blocks=blocks,
        mins=mins,
        desired=desired,
        caps=caps,
        target_total=line_count_budget,
        rng=rng,
    )

    lines: List[LineSpec] = []
    line_id = 0
    global_order = 0

    hard_neg_prob = float(content_cfg.get("hard_negative_page_prob", 0.20))

    for block_index, block in enumerate(blocks):
        bx, by, bw, bh = block.bbox
        block_type = block.block_type
        line_h = base_lh

        if block_type == "title":
            line_h = max(12, int(base_lh * 1.30))

        elif block_type == "caption":
            line_h = max(10, int(base_lh * 0.82))

        elif block_type == "equation":
            line_h = max(14, int(base_lh * 1.28))

        nlines = desired[block_index]
        line_type = _line_type_of_block(block_type)

        if nlines <= 0:
            continue

        if block_type == "table":
            rows = int(block.style.get("table_rows", 4))
            cols = int(block.style.get("table_cols", 4))

            cell_boxes = _table_cell_bboxes(
                bx,
                by,
                bw,
                bh,
                rows=rows,
                cols=cols,
                compact=bool(block.style.get("compact", False)),
                header_rows=int(block.style.get("header_rows", 0)),
                header_cols=int(block.style.get("header_cols", 0)),
                style=block.style,
            )

            for line_index, line_bbox in enumerate(cell_boxes[:nlines]):
                lines.append(
                    LineSpec(
                        line_id=line_id,
                        block_id=block.block_id,
                        line_type="table_cell",
                        line_order_in_block=line_index,
                        global_line_order=global_order,
                        bbox=line_bbox,
                        quad=None,
                        is_hard=bool(rng.random() < hard_neg_prob * 0.10),
                    )
                )

                line_id += 1
                global_order += 1

            continue

        max_lines_in_block = _max_lines_in_block(block, line_h)
        nlines = min(nlines, max_lines_in_block)

        for line_index in range(nlines):
            if block_type == "title":
                line_bbox = _title_line_bbox(bx, by, bw, bh, line_h, rng)

            elif block_type == "caption":
                line_bbox = _caption_line_bbox(bx, by, bw, bh, line_h, rng)

            elif block_type == "equation":
                line_bbox = _equation_line_bbox(
                    bx,
                    by,
                    bw,
                    bh,
                    line_h,
                    rng,
                    line_index=line_index,
                    line_count=nlines,
                )

            elif block_type == "list":
                line_bbox = _list_line_bbox(
                    bx,
                    by,
                    bw,
                    bh,
                    line_index,
                    line_h,
                    rng,
                )

            else:
                line_bbox = _paragraph_line_bbox(
                    bx,
                    by,
                    bw,
                    bh,
                    line_index,
                    nlines,
                    line_h,
                    rng,
                )

            line_bbox = _apply_line_gap_randomness(
                line_bbox,
                block_y=by,
                block_h=bh,
                line_index=line_index,
                line_count=nlines,
                line_h=line_h,
                policy=line_gap_policy,
                density_level=density_level,
                block_type=block_type,
                rng=rng,
            )

            x, y, ww, hh = line_bbox

            if y + hh > by + bh:
                break

            lines.append(
                LineSpec(
                    line_id=line_id,
                    block_id=block.block_id,
                    line_type=line_type,
                    line_order_in_block=line_index,
                    global_line_order=global_order,
                    bbox=(int(x), int(y), int(ww), int(hh)),
                    quad=None,
                    is_hard=bool(rng.random() < hard_neg_prob * 0.15),
                )
            )

            line_id += 1
            global_order += 1

    for idx, line in enumerate(lines):
        line.global_line_order = idx

    real_has_equation = any(block.block_type == "equation" for block in blocks)
    real_has_table = any(block.block_type == "table" for block in blocks)
    real_has_figure = any(block.block_type == "figure" for block in blocks)

    return PageSpec(
        page_id=page_id,
        w=w,
        h=h,
        dpi=dpi,
        page_size_name=page_size_name,
        page_width_in=page_width_in,
        page_height_in=page_height_in,
        orientation=orientation,
        page_family=page_family,
        layout_type=layout_type,
        density_level=density_level,
        scale_profile=scale_profile,
        noise_level=noise_level,
        rotation_deg=rotation_deg,
        perspective=perspective,
        has_table=real_has_table,
        has_equation=real_has_equation,
        has_figure=real_has_figure,
        blocks=blocks,
        lines=lines,
    )



