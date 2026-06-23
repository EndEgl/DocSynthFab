# src/docsynthfab/qc/bbox_utils.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _clamp_bbox_xywh(
    x: int,
    y: int,
    w: int,
    h: int,
    W: int,
    H: int,
) -> Tuple[int, int, int, int]:
    """Clamp an XYWH box to page bounds and return XYXY coordinates."""
    x0 = max(0, min(W - 1, int(x)))
    y0 = max(0, min(H - 1, int(y)))

    x1 = max(0, min(W, x0 + max(1, int(w))))
    y1 = max(0, min(H, y0 + max(1, int(h))))

    if x1 <= x0:
        x1 = min(W, x0 + 1)

    if y1 <= y0:
        y1 = min(H, y0 + 1)

    return x0, y0, x1, y1


def _xywh_to_xyxy(
    b: List[int] | Tuple[int, int, int, int],
) -> Tuple[int, int, int, int]:
    """Convert an XYWH box to XYXY coordinates."""
    x, y, w, h = map(int, b)
    return int(x), int(y), int(x + max(1, w)), int(y + max(1, h))


def _bbox_area_xywh(
    b: List[int] | Tuple[int, int, int, int],
) -> int:
    """Return the area of an XYWH box."""
    _, _, w, h = map(int, b)
    return max(0, w) * max(0, h)


def _inter_area_xyxy(
    a: Tuple[int, int, int, int],
    b: Tuple[int, int, int, int],
) -> int:
    """Return the intersection area between two XYXY boxes."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b

    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)

    if ix1 <= ix0 or iy1 <= iy0:
        return 0

    return (ix1 - ix0) * (iy1 - iy0)


def _bbox_union_extent_ratio_from_ann(
    ann: Dict[str, Any],
    page_w: int,
    page_h: int,
) -> float:
    """
    Return the extent ratio of all line bboxes in the annotation.

    This is not an exact geometric union. It is a fast outer-extent ratio
    used by production QC to reject visually tiny pages without writing
    extra debug state into the annotation JSON.
    """
    lines = ann.get("lines", []) or []

    if not isinstance(lines, list) or not lines:
        return 0.0

    xs0: list[float] = []
    ys0: list[float] = []
    xs1: list[float] = []
    ys1: list[float] = []

    for ln in lines:
        if not isinstance(ln, dict):
            continue

        b = ln.get("bbox", None)

        if not isinstance(b, (list, tuple)) or len(b) < 4:
            continue

        try:
            x, y, w, h = float(b[0]), float(b[1]), float(b[2]), float(b[3])
        except Exception:
            continue

        if w <= 0 or h <= 0:
            continue

        xs0.append(max(0.0, x))
        ys0.append(max(0.0, y))
        xs1.append(min(float(page_w), x + w))
        ys1.append(min(float(page_h), y + h))

    if not xs0:
        return 0.0

    ux0 = min(xs0)
    uy0 = min(ys0)
    ux1 = max(xs1)
    uy1 = max(ys1)

    area = max(0.0, ux1 - ux0) * max(0.0, uy1 - uy0)
    page_area = float(max(1, int(page_w) * int(page_h)))

    return float(area) / page_area



