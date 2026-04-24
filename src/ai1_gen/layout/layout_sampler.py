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
    page_size_name: str
    page_width_in: float
    page_height_in: float
    orientation: str
    page_family: str
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


# ---------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------

def _choice_dist(rng: random.Random, dist: Dict[str, float], default: str = "normal") -> str:
    if not isinstance(dist, dict) or not dist:
        return default

    items = [(str(k), max(0.0, float(v))) for k, v in dist.items()]
    total = sum(v for _, v in items)
    if total <= 0:
        return default

    r = rng.random() * total
    acc = 0.0
    for key, prob in items:
        acc += prob
        if r <= acc:
            return key
    return items[-1][0]


def _rand_range(rng: random.Random, a: int, b: int) -> int:
    if b <= a:
        return int(a)
    return rng.randint(int(a), int(b))


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _page_size_meta(size_key: str, dpi: int) -> Tuple[int, int, float, float, str]:
    size_map_in = {
        "a4_portrait": (8.27, 11.69),
        "a4_landscape": (11.69, 8.27),
        "letter_portrait": (8.5, 11.0),
        "letter_landscape": (11.0, 8.5),
        "legal_portrait": (8.5, 14.0),
        "legal_landscape": (14.0, 8.5),
        "a5_portrait": (5.83, 8.27),
        "a5_landscape": (8.27, 5.83),
        "b5_portrait": (6.93, 9.84),
        "b5_landscape": (9.84, 6.93),
        "executive_portrait": (7.25, 10.5),
        "executive_landscape": (10.5, 7.25),
        "tabloid_portrait": (11.0, 17.0),
        "tabloid_landscape": (17.0, 11.0),
    }

    w_in, h_in = size_map_in.get(size_key, size_map_in["a4_portrait"])
    w = int(round(w_in * dpi))
    h = int(round(h_in * dpi))
    orientation = "landscape" if w_in > h_in else "portrait"
    return w, h, w_in, h_in, orientation

# ---------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------

def _default_page_family_dist() -> Dict[str, float]:
    return {
        "book": 0.34,
        "academic": 0.20,
        "report": 0.18,
        "worksheet": 0.14,
        "notes": 0.14,
    }


def _default_family_layout_dist(page_family: str) -> Dict[str, float]:
    defaults: Dict[str, Dict[str, float]] = {
        "book": {"single_col": 0.74, "double_col": 0.20, "mixed_cols": 0.06},
        "academic": {"single_col": 0.10, "double_col": 0.78, "mixed_cols": 0.12},
        "report": {"single_col": 0.56, "double_col": 0.28, "mixed_cols": 0.16},
        "worksheet": {"single_col": 0.68, "double_col": 0.18, "mixed_cols": 0.14},
        "notes": {"single_col": 0.76, "double_col": 0.12, "mixed_cols": 0.12},
    }
    return defaults.get(page_family, defaults["report"])


# ---------------------------------------------------------------------
# Sampling high-level page traits
# ---------------------------------------------------------------------

def _sample_page_family(cfg, rng: random.Random) -> str:
    layout_cfg = cfg.raw.get("layout", {}) or {}
    fam_dist = layout_cfg.get("page_family_dist", _default_page_family_dist())
    return _choice_dist(rng, fam_dist, default="report")


def _sample_layout_type(cfg, rng: random.Random, page_family: str) -> str:
    layout_cfg = cfg.raw.get("layout", {}) or {}
    fam_map = layout_cfg.get("family_layout_type_dist", {}) or {}
    fam_dist = fam_map.get(page_family, _default_family_layout_dist(page_family))
    return _choice_dist(rng, fam_dist, default="single_col")

def _sample_page_size(cfg, rng: random.Random) -> str:
    page_cfg = cfg.raw.get("page", {}) or {}
    size_dist = page_cfg.get("size_dist", None)

    if isinstance(size_dist, dict) and size_dist:
        return _choice_dist(rng, size_dist, default="a4_portrait")

    size_name = str(page_cfg.get("size_name", "A4")).strip().upper()
    if size_name == "A4":
        return "a4_portrait"
    if size_name == "LETTER":
        return "letter_portrait"
    if size_name == "LEGAL":
        return "legal_portrait"

    return "a4_portrait"

def _sample_content_flags(
    page_family: str,
    rng: random.Random,
    content_cfg: Dict[str, object],
) -> Tuple[bool, bool, bool]:
    base_eq = float(content_cfg.get("has_equation_prob", 0.30))
    base_tbl = float(content_cfg.get("has_table_prob", 0.30))
    base_fig = float(content_cfg.get("has_figure_prob", 0.28))

    mult = {
        "book": {"eq": 0.85, "tbl": 0.60, "fig": 0.55},
        "academic": {"eq": 1.55, "tbl": 1.10, "fig": 1.20},
        "report": {"eq": 0.70, "tbl": 1.35, "fig": 1.10},
        "worksheet": {"eq": 1.20, "tbl": 0.85, "fig": 0.45},
        "notes": {"eq": 0.55, "tbl": 0.45, "fig": 0.35},
    }.get(page_family, {"eq": 1.0, "tbl": 1.0, "fig": 1.0})

    has_equation = rng.random() < min(0.95, base_eq * mult["eq"])
    has_table = rng.random() < min(0.95, base_tbl * mult["tbl"])
    has_figure = rng.random() < min(0.95, base_fig * mult["fig"])

    return has_equation, has_table, has_figure


def _target_counts(cfg, density_level: str, page_family: str, rng: random.Random) -> Tuple[int, int]:
    targets = cfg.density_targets()
    t = targets.get(
        density_level,
        targets.get("normal", {"line_count_range": (35, 75), "block_count_range": (8, 16)}),
    )

    line_count = _rand_range(rng, t["line_count_range"][0], t["line_count_range"][1])
    block_count = _rand_range(rng, t["block_count_range"][0], t["block_count_range"][1])

    fam_scale = {
        "book": (1.08, 0.95),
        "academic": (1.10, 1.00),
        "report": (0.96, 0.94),
        "worksheet": (0.82, 0.88),
        "notes": (0.72, 0.82),
    }.get(page_family, (1.0, 1.0))

    line_count = max(4, int(round(line_count * fam_scale[0])))
    block_count = max(1, int(round(block_count * fam_scale[1])))

    if density_level == "mixed":
        line_count = max(line_count, int(line_count * 1.10))

    return line_count, block_count


# ---------------------------------------------------------------------
# Block sequence generation
# ---------------------------------------------------------------------

def _fit_sequence_to_budget(
    seq: List[str],
    block_budget: int,
    has_figure: bool,
    has_table: bool,
    has_equation: bool,
) -> List[str]:
    out = list(seq)

    if not has_figure:
        out = [x for x in out if x != "figure"]
    if not has_table:
        out = [x for x in out if x != "table"]
    if not has_equation:
        out = [x for x in out if x != "equation"]

    cleaned: List[str] = []
    prev = None
    for item in out:
        if item == "caption" and prev not in {"figure", "table"}:
            continue
        cleaned.append(item)
        prev = item
    out = cleaned

    removable = {"paragraph", "list"}
    while len(out) > block_budget:
        idx = next((i for i in range(len(out) - 1, -1, -1) if out[i] in removable), None)
        if idx is None:
            break
        del out[idx]

    while len(out) < block_budget:
        out.append("paragraph")

    cleaned = []
    prev = None
    for item in out:
        if item == "caption" and prev not in {"figure", "table"}:
            continue
        cleaned.append(item)
        prev = item

    if not cleaned:
        cleaned = ["title", "paragraph", "paragraph"]

    return cleaned[:block_budget]


def _ensure_required_blocks(
    seq: List[str],
    block_budget: int,
    has_figure: bool,
    has_table: bool,
    has_equation: bool,
) -> List[str]:
    """
    Sample edilmiş flag'ler True ise, ilgili içerik gerçekten sequence'te en az
    bir kez bulunsun. Özellikle math_mask'in boş gelmesini azaltmak için equation
    burada garanti edilir.
    """
    out = list(seq)

    def insert_required(token: str, preferred_idx: int) -> None:
        if token in out:
            return
        idx = max(0, min(preferred_idx, len(out)))
        out.insert(idx, token)

    if has_equation:
        # Title sonrası veya ilk 2 blok içinde görünmesi math için daha güvenli
        insert_required("equation", 2)

    if has_table:
        # Tablo daha doğal olarak orta/arka kısımda dursun
        insert_required("table", min(max(3, len(out) // 2), len(out)))

    if has_figure:
        # Figure da orta/arka kısımda daha doğal görünür
        insert_required("figure", min(max(3, (len(out) // 2) + 1), len(out)))

    # Budget aşımı varsa paragraph/list silinir; required bloklar korunur
    return _fit_sequence_to_budget(
        seq=out,
        block_budget=block_budget,
        has_figure=has_figure,
        has_table=has_table,
        has_equation=has_equation,
    )


def _make_block_sequence(
    page_family: str,
    rng: random.Random,
    block_budget: int,
    has_figure: bool,
    has_table: bool,
    has_equation: bool,
    has_caption_prob: float,
) -> List[str]:
    seq: List[str] = []

    if page_family == "book":
        seq.extend(["title", "paragraph", "paragraph", "paragraph"])
        if has_figure and rng.random() < 0.58:
            seq.append("figure")
            if rng.random() < has_caption_prob:
                seq.append("caption")
        if has_equation and rng.random() < 0.42:
            seq.extend(["paragraph", "equation"])
        if has_table and rng.random() < 0.24:
            seq.append("table")
            if rng.random() < has_caption_prob * 0.65:
                seq.append("caption")
        seq.extend(["paragraph", "paragraph", "list", "paragraph"])

    elif page_family == "academic":
        seq.extend(["title", "paragraph", "paragraph", "paragraph"])
        if has_equation and rng.random() < 0.76:
            seq.extend(["equation", "paragraph"])
        if has_figure and rng.random() < 0.74:
            seq.append("figure")
            if rng.random() < max(0.75, has_caption_prob):
                seq.append("caption")
        if has_table and rng.random() < 0.58:
            seq.append("table")
            if rng.random() < max(0.72, has_caption_prob):
                seq.append("caption")
        seq.extend(["paragraph", "paragraph", "paragraph"])

    elif page_family == "report":
        seq.extend(["title", "paragraph", "paragraph"])
        if has_equation and rng.random() < 0.40:
            seq.extend(["equation", "paragraph"])
        if has_table and rng.random() < 0.66:
            seq.append("table")
            if rng.random() < has_caption_prob * 0.90:
                seq.append("caption")
        if has_figure and rng.random() < 0.50:
            seq.append("figure")
            if rng.random() < has_caption_prob:
                seq.append("caption")
        seq.extend(["paragraph", "list", "paragraph", "paragraph"])

    elif page_family == "worksheet":
        seq.extend(["title", "paragraph", "list"])
        if has_equation:
            seq.extend(["equation", "paragraph"])
        seq.extend(["list", "paragraph", "list"])
        if has_table and rng.random() < 0.34:
            seq.append("table")
        seq.extend(["paragraph", "list"])

    else:  # notes
        seq.extend(["title", "list", "paragraph", "list", "paragraph"])
        if has_equation and rng.random() < 0.24:
            seq.append("equation")
        if has_table and rng.random() < 0.14:
            seq.append("table")
        seq.extend(["list", "paragraph", "list"])

    return _ensure_required_blocks(
        seq=seq,
        block_budget=block_budget,
        has_figure=has_figure,
        has_table=has_table,
        has_equation=has_equation,
    )


# ---------------------------------------------------------------------
# Geometry / block placement
# ---------------------------------------------------------------------

def _resolve_columns(layout_type: str, page_family: str, rng: random.Random) -> int:
    if layout_type == "single_col":
        return 1
    if layout_type == "double_col":
        return 2
    if page_family == "academic":
        return 2
    return 2 if rng.random() < 0.70 else 1


def _block_height_ratio(
    block_type: str,
    density_level: str,
    page_family: str,
    rng: random.Random,
) -> float:
    base = {
        "title": (0.030, 0.050),
        "paragraph": (0.180, 0.400),
        "list": (0.120, 0.250),
        "equation": (0.060, 0.130),
        "table": (0.180, 0.350),
        "figure": (0.220, 0.450),
        "caption": (0.020, 0.035),
        "header": (0.015, 0.030),
        "footer": (0.015, 0.030),
    }.get(block_type, (0.120, 0.280))

    lo, hi = base

    if density_level == "dense":
        lo *= 1.20
        hi *= 1.45
    elif density_level == "sparse":
        lo *= 0.86
        hi *= 0.95
    elif density_level == "mixed":
        if rng.random() < 0.50:
            lo *= 0.72
            hi *= 0.92
        else:
            lo *= 1.08
            hi *= 1.28

    if page_family == "notes":
        if block_type in {"list", "paragraph"}:
            lo *= 0.92
            hi *= 1.08
    elif page_family == "worksheet":
        if block_type in {"list", "table"}:
            lo *= 1.12
            hi *= 1.22
    elif page_family == "academic":
        if block_type in {"equation", "figure"}:
            lo *= 1.18
            hi *= 1.36
        if block_type == "paragraph":
            lo *= 1.08
            hi *= 1.14

    return rng.uniform(lo, hi)


def _assign_block_positions(
    seq: List[str],
    layout_type: str,
    page_family: str,
    w: int,
    h: int,
    rng: random.Random,
    density_level: str,
    page_size_name: str,
) -> List[Tuple[int, int, int, int, int, str, Dict[str, object]]]:
    """
    Dönen tuple:
    (column_id, x, y, bw, bh, block_type, style)
    """
    ncol = _resolve_columns(layout_type, page_family, rng)

    margin_x = int(0.08 * w)
    margin_y = int(0.08 * h)
    usable_w = w - 2 * margin_x
    usable_h = h - 2 * margin_y

    gutter = int(0.03 * w) if ncol == 2 else 0
    col_w = (usable_w - gutter) // ncol if ncol == 2 else usable_w

    col_xs = [margin_x] if ncol == 1 else [margin_x, margin_x + col_w + gutter]
    col_y = [margin_y for _ in range(ncol)]

    placed: List[Tuple[int, int, int, int, int, str, Dict[str, object]]] = []

    mixed_fullwidth_budget = 0
    if layout_type == "mixed_cols":
        mixed_fullwidth_budget = 2 if seq and seq[0] == "title" else 1

    current_col = 0
    prev_item: Optional[Tuple[int, int, int, int, int, str, Dict[str, object]]] = None

    bottom_limit = h - margin_y

    for i, block_type in enumerate(seq):
        bh = int(_block_height_ratio(block_type, density_level, page_family, rng) * h)
        bh = _clamp(bh, 24, max(40, int(usable_h * 0.82)))

        style: Dict[str, object] = {
            "page_family": page_family,
            "layout_type": layout_type,
            "page_size_name": page_size_name,
            "orientation": "landscape" if w > h else "portrait",
        }

        if block_type == "caption" and prev_item is not None and prev_item[5] in {"figure", "table"}:
            prev_col, prev_x, prev_y, prev_bw, prev_bh, _, _ = prev_item
            cap_h = max(22, int(bh * 0.65))
            cap_gap = int(rng.uniform(0.003, 0.007) * h)
            x = prev_x
            y = prev_y + prev_bh + cap_gap
            bw = prev_bw
            bh = cap_h

            if y + bh > bottom_limit:
                bh = max(16, bottom_limit - y)

            if prev_col == -1:
                for c in range(ncol):
                    col_y[c] = max(col_y[c], y + bh + cap_gap)
                column_id = -1
                style["full_width"] = True
            else:
                col_y[prev_col] = max(col_y[prev_col], y + bh + cap_gap)
                column_id = prev_col

            style["caption_of_prev"] = True
            placed_item = (column_id, x, y, bw, bh, block_type, style)
            placed.append(placed_item)
            prev_item = placed_item
            continue

        full_width = False
        if block_type == "title":
            full_width = True
        elif layout_type == "mixed_cols" and i < mixed_fullwidth_budget:
            full_width = True
        elif block_type == "table" and ncol == 2 and rng.random() < 0.45:
            full_width = True
        elif block_type == "figure" and page_family in {"report", "book"} and ncol == 2 and rng.random() < 0.22:
            full_width = True

        if full_width:
            x = margin_x
            y = max(col_y)
            bw = usable_w
            gap = int(rng.uniform(0.015, 0.030) * h) if block_type == "title" else int(rng.uniform(0.005, 0.012) * h)

            if y + bh > bottom_limit:
                bh = max(24, bottom_limit - y)

            for c in range(ncol):
                col_y[c] = y + bh + gap

            column_id = -1
            style["full_width"] = True
            placed_item = (column_id, x, y, bw, bh, block_type, style)
            placed.append(placed_item)
            prev_item = placed_item
            continue

        if ncol == 1:
            current_col = 0
        else:
            if layout_type == "double_col":
                if col_y[current_col] + bh > bottom_limit and current_col < ncol - 1:
                    current_col += 1
            else:
                current_col = 0 if col_y[0] <= col_y[1] else 1

        current_col = _clamp(current_col, 0, ncol - 1)

        x = col_xs[current_col]
        y = col_y[current_col]
        bw = col_w

        if y + bh > bottom_limit and ncol == 2:
            other = 1 - current_col
            if col_y[other] + bh <= bottom_limit:
                current_col = other
                x = col_xs[current_col]
                y = col_y[current_col]

        if y + bh > bottom_limit:
            bh = max(24, bottom_limit - y)

        gap = int(rng.uniform(0.005, 0.012) * h)
        col_y[current_col] = y + bh + gap

        column_id = current_col
        placed_item = (column_id, x, y, bw, bh, block_type, style)
        placed.append(placed_item)
        prev_item = placed_item

    return placed


# ---------------------------------------------------------------------
# Line planning
# ---------------------------------------------------------------------
def _sample_base_pt(rng: random.Random) -> float:
    """2 ile 48 punto arası ağırlıklı font seçimi yapar."""
    r = rng.random()
    if r < 0.05:
        return rng.uniform(2.0, 8.0)    # %5 İhtimal: Çok küçük yazılar
    elif r < 0.70:
        return rng.choice([9.0, 9.5, 10.0, 10.5, 11.0, 11.5]) # %65 İhtimal: Standart (Ağırlıklı)
    elif r < 0.90:
        return rng.uniform(12.0, 20.0)  # %20 İhtimal: Büyük/Orta başlık tarzı
    else:
        return rng.uniform(21.0, 48.0)  # %10 İhtimal: Dev puntolar

def _line_height_px(h: int, density_level: str, dpi: int, page_family: str, rng: random.Random) -> int:
    base_pt = _sample_base_pt(rng)
    # Puntoyu piksele çevir (1 pt = 1/72 inç)
    base_px = int(base_pt * (dpi / 72.0))
    
    if density_level == "dense":
        base = int(base_px * 1.15)
    elif density_level == "sparse":
        base = int(base_px * 1.80)
    else:
        base = int(base_px * 1.40)

    if page_family == "notes":
        base = int(base * 0.92)
    elif page_family == "worksheet":
        base = int(base * 0.96)

    return max(10, base)

def _line_type_of_block(block_type: str) -> str:
    if block_type == "equation":
        return "math"
    if block_type == "caption":
        return "caption"
    if block_type == "table":
        return "table_cell"
    return "text"


def _table_shape_for_block(
    bw: int,
    bh: int,
    density_level: str,
    page_family: str,
    rng: random.Random,
) -> Tuple[int, int, Dict[str, object]]:
    """
    cols, rows ve basit stil metadata döndürür.
    Böylece tablolar sadece boyut olarak değil, karakter olarak da çeşitlenir.
    """
    families = {
        "worksheet": [
            {"kind": "worksheet_grid", "cols": (2, 4), "rows": (4, 8)},
            {"kind": "attendance_like", "cols": (3, 5), "rows": (5, 9)},
        ],
        "academic": [
            {"kind": "stat_table", "cols": (3, 5), "rows": (4, 7)},
            {"kind": "result_matrix", "cols": (4, 6), "rows": (3, 5)},
        ],
        "report": [
            {"kind": "financial_wide", "cols": (4, 7), "rows": (3, 6)},
            {"kind": "summary_table", "cols": (3, 5), "rows": (4, 6)},
        ],
        "book": [
            {"kind": "book_reference", "cols": (3, 5), "rows": (4, 7)},
            {"kind": "comparison_table", "cols": (4, 6), "rows": (3, 5)},
        ],
        "notes": [
            {"kind": "compact_notes", "cols": (2, 4), "rows": (3, 6)},
            {"kind": "quick_grid", "cols": (3, 4), "rows": (3, 5)},
        ],
    }

    presets = families.get(page_family, families["report"])
    preset = rng.choice(presets)

    cols = rng.randint(*preset["cols"])
    rows = rng.randint(*preset["rows"])

    # density etkisi
    if density_level == "dense":
        rows += rng.randint(1, 2)
        if rng.random() < 0.45:
            cols += 1
    elif density_level == "sparse":
        rows = max(2, rows - rng.randint(0, 2))
        if rng.random() < 0.35:
            cols = max(2, cols - 1)
    elif density_level == "mixed":
        if rng.random() < 0.50:
            rows += rng.randint(1, 2)
        else:
            cols += rng.randint(0, 1)

    # bbox oranına göre yatay/dikey masa karakteri
    aspect = bw / max(1, bh)
    if aspect > 1.8 and rng.random() < 0.65:
        cols = max(cols, rng.randint(5, 7))
        rows = min(rows, rng.randint(3, 5))
        table_variant = "wide"
    elif aspect < 0.9 and rng.random() < 0.55:
        rows = max(rows, rng.randint(6, 9))
        cols = min(cols, rng.randint(2, 4))
        table_variant = "tall"
    else:
        table_variant = "balanced"

    cols = max(2, cols)
    rows = max(2, rows)

    if page_family == "worksheet":
        border_dist = {
            "full_grid": 0.42,
            "rows_only": 0.18,
            "cols_only": 0.08,
            "outer_only": 0.10,
            "header_rule": 0.05,
            "ledger": 0.12,
            "borderless": 0.05,
        }
    elif page_family == "academic":
        border_dist = {
            "full_grid": 0.24,
            "rows_only": 0.22,
            "cols_only": 0.08,
            "outer_only": 0.08,
            "header_rule": 0.20,
            "ledger": 0.06,
            "borderless": 0.12,
        }
    elif page_family == "report":
        border_dist = {
            "full_grid": 0.28,
            "rows_only": 0.22,
            "cols_only": 0.08,
            "outer_only": 0.10,
            "header_rule": 0.16,
            "ledger": 0.06,
            "borderless": 0.10,
        }
    elif page_family == "notes":
        border_dist = {
            "full_grid": 0.14,
            "rows_only": 0.18,
            "cols_only": 0.05,
            "outer_only": 0.08,
            "header_rule": 0.10,
            "ledger": 0.05,
            "borderless": 0.40,
        }
    else:
        border_dist = {
            "full_grid": 0.24,
            "rows_only": 0.20,
            "cols_only": 0.08,
            "outer_only": 0.10,
            "header_rule": 0.12,
            "ledger": 0.06,
            "borderless": 0.20,
        }

    style = {
        "table_kind": preset["kind"],
        "table_variant": table_variant,
        "header_rows": 1 if rng.random() < 0.88 else 0,
        "header_cols": 1 if rng.random() < 0.35 else 0,
        "compact": bool(rng.random() < 0.45),
        "border_mode": _choice_dist(rng, border_dist, default="full_grid"),
        "zebra_rows": bool(rng.random() < 0.30),
        "light_rules": bool(rng.random() < 0.55),
    }
    return cols, rows, style



def _max_lines_in_block(block: BlockSpec, base_lh: int) -> int:
    _, _, _, bh = block.bbox
    return max(1, bh // max(8, base_lh))


def _initial_line_plan(
    blocks: List[BlockSpec],
    base_lh: int,
    page_family: str,
    density_level: str,
    rng: random.Random,
) -> Tuple[List[int], List[int], List[int]]:
    """
    returns: mins, desired, caps
    """
    mins: List[int] = []
    desired: List[int] = []
    caps: List[int] = []

    for b in blocks:
        btype = b.block_type
        cap = _max_lines_in_block(b, base_lh)

        if btype == "title":
            mn = des = 1
            cap = max(1, cap)
        elif btype == "equation":
            mn = des = 1
            cap = max(1, cap)
        elif btype == "figure":
            mn = des = 0
            cap = 0
        elif btype == "caption":
            mn = des = 1
            cap = max(1, min(cap, 2))

        elif btype == "table":
            cols, rows, table_style = _table_shape_for_block(
                b.bbox[2], b.bbox[3], density_level, page_family, rng
            )
            b.style["table_cols"] = cols
            b.style["table_rows"] = rows
            b.style.update(table_style)

            cells = cols * rows

            # Bazı tablolarda her hücre dolu olmaz; biraz doğal boşluk bırak
            fill_ratio = 1.0
            if table_style.get("table_variant") == "wide":
                fill_ratio = rng.uniform(0.78, 0.96)
            elif table_style.get("table_variant") == "tall":
                fill_ratio = rng.uniform(0.82, 0.98)
            else:
                fill_ratio = rng.uniform(0.80, 1.00)

            desired_cells = max(2, int(round(cells * fill_ratio)))
            cap = max(desired_cells, cap)
            mn = max(2, min(cells, desired_cells))
            des = max(mn, min(cells, desired_cells))






        elif btype == "list":
            mn = 2 if cap >= 2 else 1
            if density_level == "dense":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.68, 0.95)))))
            elif density_level == "sparse":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.45, 0.70)))))
            else:
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.55, 0.86)))))
        else:
            mn = 2 if cap >= 2 else 1
            if page_family == "notes":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.45, 0.72)))))
            elif page_family == "worksheet":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.40, 0.68)))))
            elif density_level == "dense":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.72, 0.98)))))
            elif density_level == "sparse":
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.48, 0.74)))))
            else:
                des = max(mn, min(cap, int(round(cap * rng.uniform(0.58, 0.90)))))

        mins.append(mn)
        desired.append(des)
        caps.append(cap)

    return mins, desired, caps


def _rebalance_line_counts(
    blocks: List[BlockSpec],
    mins: List[int],
    desired: List[int],
    caps: List[int],
    target_total: int,
    rng: random.Random,
) -> List[int]:
    out = list(desired)
    cur = sum(out)

    growable = [i for i, b in enumerate(blocks) if b.block_type in {"paragraph", "list"}]
    shrinkable = [i for i, b in enumerate(blocks) if b.block_type in {"paragraph", "list"}]

    guard = 0
    while cur < target_total and guard < 200000:
        guard += 1
        candidates = [i for i in growable if out[i] < caps[i]]
        if not candidates:
            break
        candidates.sort(key=lambda i: (caps[i] - out[i], blocks[i].bbox[3]), reverse=True)
        top = candidates[: min(6, len(candidates))]
        pick = rng.choice(top)
        out[pick] += 1
        cur += 1

    guard = 0
    while cur > target_total and guard < 200000:
        guard += 1
        candidates = [i for i in shrinkable if out[i] > mins[i]]
        if not candidates:
            break
        candidates.sort(key=lambda i: (out[i] - mins[i], blocks[i].bbox[3]), reverse=True)
        top = candidates[: min(6, len(candidates))]
        pick = rng.choice(top)
        out[pick] -= 1
        cur -= 1

    return out


# ---------------------------------------------------------------------
# Line bbox generation
# ---------------------------------------------------------------------

def _paragraph_line_bbox(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    j: int,
    nlines: int,
    lh: int,
    rng: random.Random,
) -> Tuple[int, int, int, int]:
    y = by + int(0.10 * bh) + j * lh
    xpad = int(0.03 * bw)

    if j == 0 and rng.random() < 0.72:
        xpad += int(0.05 * bw)

    if j == nlines - 1 and nlines > 1:
        line_w = int(bw * rng.uniform(0.35, 0.76))
    else:
        if rng.random() < 0.52:
            line_w = int((bw - xpad) * rng.uniform(0.96, 1.00))
        else:
            line_w = int((bw - xpad) * rng.uniform(0.88, 0.95))

    line_w = max(12, min(line_w, bw - xpad - 4))
    line_h = max(6, lh - int(0.30 * lh))
    x = bx + xpad
    y = y + int(0.15 * lh)
    return x, y, line_w, line_h


def _list_line_bbox(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    j: int,
    lh: int,
    rng: random.Random,
) -> Tuple[int, int, int, int]:
    y = by + int(0.10 * bh) + j * lh
    xpad = int(0.03 * bw) + int(0.04 * bw)
    line_w = int((bw - xpad) * rng.uniform(0.82, 0.95))
    line_w = max(12, min(line_w, bw - xpad - 4))
    line_h = max(6, lh - int(0.30 * lh))
    x = bx + xpad
    y = y + int(0.15 * lh)
    return x, y, line_w, line_h


def _title_line_bbox(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    lh: int,
    rng: random.Random,
) -> Tuple[int, int, int, int]:
    xpad = int(0.02 * bw)
    line_w = int((bw - xpad) * rng.uniform(0.45, 0.82))
    line_w = max(18, min(line_w, bw - xpad - 4))
    line_h = max(8, lh - int(0.22 * lh))
    x = bx + xpad
    y = by + int(0.12 * bh)
    return x, y, line_w, line_h


def _caption_line_bbox(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    lh: int,
    rng: random.Random,
) -> Tuple[int, int, int, int]:
    xpad = int(0.01 * bw)
    line_w = int((bw - xpad) * rng.uniform(0.55, 0.96))
    line_w = max(16, min(line_w, bw - xpad - 4))
    line_h = max(6, lh - int(0.30 * lh))
    x = bx + xpad
    y = by + int(0.10 * bh)
    return x, y, line_w, line_h


def _equation_line_bbox(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    lh: int,
    rng: random.Random,
) -> Tuple[int, int, int, int]:
    xpad = int(0.08 * bw)
    line_w = int((bw - 2 * xpad) * rng.uniform(0.65, 0.90))
    line_w = max(24, min(line_w, bw - 2 * xpad))
    line_h = max(16, int(min(bh * 0.78, lh * 1.35)))
    x = bx + (bw - line_w) // 2
    y = by + max(0, (bh - line_h) // 2)
    return x, y, line_w, line_h

def _table_cell_bboxes(
    bx: int,
    by: int,
    bw: int,
    bh: int,
    rows: int,
    cols: int,
    *,
    compact: bool = False,
    header_rows: int = 0,
    header_cols: int = 0,
) -> List[Tuple[int, int, int, int]]:
    cells: List[Tuple[int, int, int, int]] = []

    cell_w = max(12, bw // cols)
    cell_h = max(12, bh // rows)

    if compact:
        pad_x = max(2, int(cell_w * 0.06))
        pad_y = max(2, int(cell_h * 0.10))
    else:
        pad_x = max(3, int(cell_w * 0.10))
        pad_y = max(3, int(cell_h * 0.18))

    for r in range(rows):
        for c in range(cols):
            x0 = bx + c * cell_w
            y0 = by + r * cell_h

            # header satır/sütunları biraz daha iç boşluklu olsun
            px = pad_x
            py = pad_y
            if r < header_rows:
                py = max(2, int(py * 0.75))
            if c < header_cols:
                px = max(2, int(px * 0.75))

            x = x0 + px
            y = y0 + py
            ww = max(8, cell_w - 2 * px)
            hh = max(8, cell_h - 2 * py)

            cells.append((x, y, ww, hh))

    return cells
# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def sample_page_spec(cfg, rng: random.Random, page_index: int, page_id: str) -> PageSpec:
    density_level = _choice_dist(rng, cfg.density_dist(), default="normal")
    scale_profile = _choice_dist(rng, cfg.scale_dist(), default="dpi300")
    noise_level = _choice_dist(rng, cfg.noise_dist(), default="medium")

    dpi = 200 if scale_profile == "dpi200" else 300
    page_size_name = _sample_page_size(cfg, rng)
    w, h, page_width_in, page_height_in, orientation = _page_size_meta(page_size_name, dpi)


    content_cfg = cfg.raw.get("content", {}) or {}
    page_family = _sample_page_family(cfg, rng)
    layout_type = _sample_layout_type(cfg, rng, page_family)

    sampled_has_equation, sampled_has_table, sampled_has_figure = _sample_content_flags(page_family, rng, content_cfg)

    rotation_deg = float(rng.uniform(-2.0, 2.0))
    perspective = bool(rng.random() < 0.25)

    line_count_budget, block_count_budget = _target_counts(cfg, density_level, page_family, rng)
    has_caption_prob = float(content_cfg.get("has_caption_prob", 0.35))

    seq = _make_block_sequence(
        page_family=page_family,
        rng=rng,
        block_budget=block_count_budget,
        has_figure=sampled_has_figure,
        has_table=sampled_has_table,
        has_equation=sampled_has_equation,
        has_caption_prob=has_caption_prob,
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

    for bi, b in enumerate(blocks):
        bx, by, bw, bh = b.bbox
        block_type = b.block_type

        lh = base_lh
        if block_type == "title":
            lh = max(12, int(base_lh * 1.30))
        elif block_type == "caption":
            lh = max(10, int(base_lh * 0.82))
        elif block_type == "equation":
            lh = max(14, int(base_lh * 1.28))

        nlines = desired[bi]
        line_type = _line_type_of_block(block_type)

        if nlines <= 0:
            continue

        if block_type == "table":
            rows = int(b.style.get("table_rows", 4))
            cols = int(b.style.get("table_cols", 4))
            cell_boxes = _table_cell_bboxes(
                bx,
                by,
                bw,
                bh,
                rows=rows,
                cols=cols,
                compact=bool(b.style.get("compact", False)),
                header_rows=int(b.style.get("header_rows", 0)),
                header_cols=int(b.style.get("header_cols", 0)),
            )
            
            for j, lb in enumerate(cell_boxes[:nlines]):
                lines.append(
                    LineSpec(
                        line_id=line_id,
                        block_id=b.block_id,
                        line_type="table_cell",
                        line_order_in_block=j,
                        global_line_order=global_order,
                        bbox=lb,
                        quad=None,
                        is_hard=bool(rng.random() < hard_neg_prob * 0.10),
                    )
                )
                line_id += 1
                global_order += 1
            continue

        max_lines_in_block = _max_lines_in_block(b, lh)
        nlines = min(nlines, max_lines_in_block)

        for j in range(nlines):
            if block_type == "title":
                lb = _title_line_bbox(bx, by, bw, bh, lh, rng)
            elif block_type == "caption":
                lb = _caption_line_bbox(bx, by, bw, bh, lh, rng)
            elif block_type == "equation":
                lb = _equation_line_bbox(bx, by, bw, bh, lh, rng)
            elif block_type == "list":
                lb = _list_line_bbox(bx, by, bw, bh, j, lh, rng)
            else:
                lb = _paragraph_line_bbox(bx, by, bw, bh, j, nlines, lh, rng)

            x, y, ww, hh = lb
            if y + hh > by + bh:
                break

            lines.append(
                LineSpec(
                    line_id=line_id,
                    block_id=b.block_id,
                    line_type=line_type,
                    line_order_in_block=j,
                    global_line_order=global_order,
                    bbox=(int(x), int(y), int(ww), int(hh)),
                    quad=None,
                    is_hard=bool(rng.random() < hard_neg_prob * 0.15),
                )
            )
            line_id += 1
            global_order += 1


    for k, ln in enumerate(lines):
        ln.global_line_order = k

    real_has_equation = any(b.block_type == "equation" for b in blocks)
    real_has_table = any(b.block_type == "table" for b in blocks)
    real_has_figure = any(b.block_type == "figure" for b in blocks)

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