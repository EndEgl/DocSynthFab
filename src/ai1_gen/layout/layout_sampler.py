# src/ai1_gen/layout/layout_sampler.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import random


@dataclass
class BlockSpec:
    block_id: int
    block_type: str  # paragraph/list/title/footer/header/table/figure/caption/equation
    block_order: int
    column_id: int
    bbox: Tuple[int, int, int, int]  # x,y,w,h
    style: Dict[str, object]


@dataclass
class LineSpec:
    line_id: int
    block_id: int
    line_type: str  # text/math/caption/table_cell
    line_order_in_block: int
    global_line_order: int
    bbox: Tuple[int, int, int, int]
    quad: Optional[List[Tuple[float, float]]] = None
    is_hard: bool = False


@dataclass
class PageSpec:
    page_id: str
    w: int
    h: int
    dpi: int
    layout_type: str
    density_level: str
    scale_profile: str
    noise_level: str
    rotation_deg: float
    perspective: bool
    has_table: bool
    has_equation: bool
    has_figure: bool
    blocks: List[BlockSpec]
    lines: List[LineSpec]


def _choice_dist(rng: random.Random, dist: Dict[str, float]) -> str:
    items = list(dist.items())
    r = rng.random()
    acc = 0.0
    for k, p in items:
        acc += float(p)
        if r <= acc:
            return str(k)
    return str(items[-1][0])


def _rand_range(rng: random.Random, a: int, b: int) -> int:
    if b <= a:
        return a
    return rng.randint(a, b)


def sample_page_spec(cfg, rng: random.Random, page_index: int, page_id: str) -> PageSpec:
    density_level = _choice_dist(rng, cfg.density_dist())
    scale_profile = _choice_dist(rng, cfg.scale_dist())
    noise_level = _choice_dist(rng, cfg.noise_dist())

    # DPI seçimi (scale_profile)
    if scale_profile == "dpi200":
        dpi = 200
    elif scale_profile == "dpi300":
        dpi = 300
    else:
        # lowres_capture / hires_crop gibi profillerde DPI 300 baz alınır
        dpi = 300

    # A4 px boyutu ~ 8.27x11.69 inch
    w = int(8.27 * dpi)
    h = int(11.69 * dpi)

    layout_type = _choice_dist(rng, cfg.raw.get("layout", {}).get("layout_type_dist", {
        "single_col": 0.65, "double_col": 0.30, "mixed_cols": 0.05
    }))

    # Edge content
    content = cfg.raw.get("content", {})
    has_equation = rng.random() < float(content.get("has_equation_prob", 0.35))
    has_table = rng.random() < float(content.get("has_table_prob", 0.20))
    has_figure = rng.random() < float(content.get("has_figure_prob", 0.20))

    # Geometry meta (augment’te uygulanacak)
    rotation_deg = float(rng.uniform(-2.0, 2.0))
    perspective = bool(rng.random() < 0.25)

    targets = cfg.density_targets()
    t = targets.get(density_level, targets.get("normal", {"line_count_range": (25, 60), "block_count_range": (6, 14)}))
    line_count = _rand_range(rng, t["line_count_range"][0], t["line_count_range"][1])
    block_count = _rand_range(rng, t["block_count_range"][0], t["block_count_range"][1])

    # Mixed: bant bazlı varyasyon için line_count genişlet
    if density_level == "mixed":
        line_count = max(line_count, int(line_count * 1.1))

    # Kolonlar
    if layout_type == "single_col":
        ncol = 1
    elif layout_type == "double_col":
        ncol = 2
    else:
        ncol = 2 if rng.random() < 0.7 else 1

    margin = int(0.06 * min(w, h))
    gutter = int(0.03 * w) if ncol == 2 else 0
    col_w = (w - 2 * margin - gutter) // ncol

    # Block bbox’larını üret
    blocks: List[BlockSpec] = []
    y_cursor = margin
    blk_id = 0
    for i in range(block_count):
        col = i % ncol
        x = margin + col * (col_w + gutter)
        # block height bandı
        bh = int(rng.uniform(0.05, 0.14) * h)
        if y_cursor + bh > h - margin:
            y_cursor = margin
        y = y_cursor
        y_cursor += bh + int(rng.uniform(0.01, 0.03) * h)

        # type seçimi (basit)
        if i == 0 and rng.random() < 0.7:
            btype = "title"
        elif has_equation and rng.random() < 0.12:
            btype = "equation"
        elif has_table and rng.random() < 0.10:
            btype = "table"
        elif has_figure and rng.random() < 0.10:
            btype = "figure"
        elif rng.random() < 0.15:
            btype = "list"
        else:
            btype = "paragraph"

        style = {}
        # hires_crop’ta local scale zorunluluğunu ileride renderer enforce edecek
        blocks.append(BlockSpec(
            block_id=blk_id,
            block_type=btype,
            block_order=i,
            column_id=col,
            bbox=(x, y, col_w, bh),
            style=style
        ))
        blk_id += 1

    # Line bbox’ları: block içinde üstten alta
    lines: List[LineSpec] = []
    line_id = 0
    global_order = 0

    # font size dağılımından kaba “satır yüksekliği” çıkaracağız
    style_cfg = cfg.raw.get("style", {})
    # basit: density’e göre line height
    base_lh = int(0.018 * h) if density_level in ("dense",) else int(0.022 * h)
    if dpi == 200:
        base_lh = int(base_lh * 0.9)

    for b in blocks:
        bx, by, bw, bh = b.bbox
        max_lines_in_block = max(1, bh // max(8, base_lh))
        # block type’e göre
        if b.block_type == "title":
            nlines = 1
        elif b.block_type == "equation":
            nlines = 1
        elif b.block_type == "figure":
            nlines = 0
        elif b.block_type == "table":
            nlines = max(2, min(6, max_lines_in_block))
        else:
            nlines = max(1, min(max_lines_in_block, int(rng.uniform(0.5, 1.0) * max_lines_in_block)))

        y0 = by + int(0.12 * bh)
        for j in range(nlines):
            if global_order >= line_count:
                break
            lh = base_lh
            ly = y0 + j * lh
            if ly + lh > by + bh - int(0.08 * bh):
                break
            # satır bbox: küçük padding
            xpad = int(0.03 * bw)
            ypad = int(0.15 * lh)
            lb = (bx + xpad, ly + ypad, bw - 2 * xpad, max(6, lh - 2 * ypad))

            if b.block_type == "equation":
                ltype = "math"
            elif b.block_type == "caption":
                ltype = "caption"
            elif b.block_type == "table":
                ltype = "table_cell"
            else:
                ltype = "text"

            lines.append(LineSpec(
                line_id=line_id,
                block_id=b.block_id,
                line_type=ltype,
                line_order_in_block=j,
                global_line_order=global_order,
                bbox=lb,
                quad=None,
                is_hard=bool(rng.random() < float(cfg.raw.get("content", {}).get("hard_negative_page_prob", 0.30)) * 0.15),
            ))
            line_id += 1
            global_order += 1

    # global_line_order kesintisiz kalsın
    for k, ln in enumerate(lines):
        ln.global_line_order = k

    return PageSpec(
        page_id=page_id,
        w=w,
        h=h,
        dpi=dpi,
        layout_type=layout_type,
        density_level=density_level,
        scale_profile=scale_profile,
        noise_level=noise_level,
        rotation_deg=rotation_deg,
        perspective=perspective,
        has_table=has_table,
        has_equation=has_equation,
        has_figure=has_figure,
        blocks=blocks,
        lines=lines,
    )