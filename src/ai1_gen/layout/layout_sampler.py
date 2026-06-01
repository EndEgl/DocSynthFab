# src/ai1_gen/layout/layout_sampler.py
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
from .line_gap import _apply_line_gap_randomness
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


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------


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

    line_gap_random_scale = float(layout_cfg.get("line_gap_random_scale", 0.0))

    table_diversity_scale = float(layout_cfg.get("table_diversity_scale", 0.75))
    table_empty_cell_scale = float(layout_cfg.get("table_empty_cell_scale", 0.35))
    table_merge_cell_scale = float(layout_cfg.get("table_merge_cell_scale", 0.25))

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

    blocks: List[BlockSpec] = []

    for block_id, (col, x, y, bw, bh, block_type, style) in enumerate(placed):
        column_id = 0 if col == -1 else col

        blocks.append(
            BlockSpec(
                block_id=block_id,
                block_type=block_type,
                block_order=block_id,
                column_id=column_id,
                bbox=(int(x), int(y), int(bw), int(bh)),
                style=dict(style),
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
                scale=line_gap_random_scale,
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