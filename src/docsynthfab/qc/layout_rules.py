# src/docsynthfab/qc/layout_rules.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .bbox_utils import (
    _bbox_area_xywh,
    _inter_area_xyxy,
    _xywh_to_xyxy,
)


def _collect_blocks_by_type(
    ann: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    """Group annotation blocks by block_type."""
    out: Dict[str, List[Dict[str, Any]]] = {}

    for b in ann.get("blocks", []) or []:
        bt = str(b.get("block_type", ""))
        out.setdefault(bt, []).append(b)

    return out


def _validate_block_overlaps(
    ann: Dict[str, Any],
    max_iou_like: float = 0.35,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Reject blocks that overlap too much.

    The overlap ratio is measured against the smaller block area, not IoU.
    """
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


def _validate_title_position(
    ann: Dict[str, Any],
    H: int,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate that title blocks are placed near the top of the page."""
    titles = [
        b
        for b in ann.get("blocks", []) or []
        if str(b.get("block_type", "")) == "title"
    ]

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


def _validate_caption_proximity(
    ann: Dict[str, Any],
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate that captions are near a figure-like or table-like block."""
    blocks = ann.get("blocks", []) or []

    figs_tbls = [
        b
        for b in blocks
        if str(b.get("block_type", "")) in {"figure", "auto_figure", "table", "auto_table"}
    ]

    captions = [
        b
        for b in blocks
        if str(b.get("block_type", "")) == "caption"
    ]

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

            dist = (
                (cap_center_x - fig_center_x) ** 2
                + (cap_center_y - fig_center_y) ** 2
            ) ** 0.5

            if best is None or dist < best[0]:
                best = (dist, fb)

        if best is None:
            continue

        dist, fb = best
        _, _, _, fh = map(int, fb.get("bbox", [0, 0, 0, 0]))

        allowed = max(fh * 1.35, ch * 8.0, 80.0)

        if dist > allowed:
            return False, {
                "caption_block_id": cap.get("block_id"),
                "nearest_block_id": fb.get("block_id"),
                "distance": float(dist),
                "allowed": float(allowed),
            }

    return True, None


def _validate_line_boxes(
    ann: Dict[str, Any],
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Reject line bboxes that are too small to be useful."""
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


def _validate_reading_order_soft(
    ann: Dict[str, Any],
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Softly validate reading order.

    This check allows some jumps, especially on multi-column pages, but rejects
    extremely suspicious ordering.
    """
    lines = sorted(
        ann.get("lines", []) or [],
        key=lambda z: int(z.get("global_line_order", 0)),
    )

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


def _validate_page_family_rules(
    ann: Dict[str, Any],
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validate high-level page-family expectations.

    Pure table-only and latex-only modes skip title/body requirements because
    those modes intentionally generate homogeneous content.
    """
    meta = ann.get("meta", {}) or {}

    if bool(meta.get("_fallback", False)):
        return True, None

    content_pure_mode = str(meta.get("content_pure_mode", "mixed"))

    if content_pure_mode in {"table_only", "latex_only"}:
        return True, None

    page_family = str(meta.get("page_family", "report"))
    blocks_by_type = _collect_blocks_by_type(ann)

    if page_family in {"academic", "book", "report", "worksheet", "notes"}:
        if not blocks_by_type.get("title"):
            return False, {
                "page_family": page_family,
                "reason": "missing-title",
            }

    if page_family == "academic":
        has_body = bool(blocks_by_type.get("paragraph")) or bool(blocks_by_type.get("list"))

        if not has_body:
            return False, {
                "page_family": page_family,
                "reason": "missing-body",
            }

    return True, None



