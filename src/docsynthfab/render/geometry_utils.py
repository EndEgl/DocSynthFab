# src/docsynthfab/render/geometry_utils.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from docsynthfab.layout.layout_sampler import PageSpec


def _clamp_box(
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    w: int,
    h: int,
) -> Tuple[int, int, int, int]:
    x0 = max(0, min(w - 1, x0))
    y0 = max(0, min(h - 1, y0))
    x1 = max(0, min(w, x1))
    y1 = max(0, min(h, y1))

    if x1 <= x0:
        x1 = min(w, x0 + 1)

    if y1 <= y0:
        y1 = min(h, y0 + 1)

    return x0, y0, x1, y1


def _intersects(
    a: Tuple[int, int, int, int],
    b: Tuple[int, int, int, int],
) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b

    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def _pad_box(
    b: Tuple[int, int, int, int],
    pad: int,
    w: int,
    h: int,
) -> Tuple[int, int, int, int]:
    x0, y0, x1, y1 = b
    return _clamp_box(x0 - pad, y0 - pad, x1 + pad, y1 + pad, w, h)


def _jump_past_obstacle(
    lbox: Tuple[int, int, int, int],
    obstacles: List[Tuple[int, int, int, int]],
    ycur: int,
    *,
    gap: int = 2,
) -> int:
    hit_y1 = None

    for ob in obstacles:
        if _intersects(lbox, ob):
            hit_y1 = max(hit_y1 or 0, ob[3])

    if hit_y1 is None:
        return ycur

    return max(ycur + 1, int(hit_y1 + gap))


def _try_relocate_line_bbox_down(
    x: int,
    y: int,
    ww: int,
    hh: int,
    obstacles: List[Tuple[int, int, int, int]],
    *,
    w: int,
    h: int,
    y_max: int,
    tries: int = 10,
    gap: int = 15,
) -> Tuple[bool, Tuple[int, int, int, int]]:
    ycur = int(y)

    for _ in range(tries):
        lbox = (x, ycur, x + ww, ycur + hh)

        if not any(_intersects(lbox, ob) for ob in obstacles):
            return True, (x, ycur, ww, hh)

        y_next = _jump_past_obstacle(lbox, obstacles, ycur, gap=gap)

        if y_next == ycur:
            y_next += gap

        if y_next + hh > y_max:
            break

        ycur = int(y_next)

    return False, (x, y, ww, hh)


def _line_kind_from_block(block_type: str) -> str:
    if block_type == "title":
        return "title"

    if block_type == "caption":
        return "caption"

    if block_type == "table":
        return "table_cell"

    if block_type == "list":
        return "list"

    return "text"


def _collect_block_line_map(page_spec: PageSpec) -> Dict[int, List[Any]]:
    out: Dict[int, List[Any]] = {}

    for ln in page_spec.lines:
        out.setdefault(int(ln.block_id), []).append(ln)

    for bid in out:
        out[bid].sort(key=lambda z: (int(z.line_order_in_block), int(z.global_line_order)))

    return out



