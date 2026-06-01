# src/ai1_gen/layout/occupancy.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


PlacedBlock = Tuple[int, int, int, int, int, str, Dict[str, object]]


@dataclass
class OccupancyRect:
    x: int
    y: int
    w: int
    h: int
    kind: str = "block"

    @property
    def x1(self) -> int:
        return int(self.x + self.w)

    @property
    def y1(self) -> int:
        return int(self.y + self.h)

    @property
    def area(self) -> int:
        return max(0, int(self.w)) * max(0, int(self.h))

    @property
    def center(self) -> Tuple[float, float]:
        return (
            float(self.x + self.w / 2.0),
            float(self.y + self.h / 2.0),
        )


class PageOccupancy:
    """
    RAM-only page-local placement helper.

    Contract:
    - Used only during layout sampling.
    - Never written into PageSpec, BlockSpec, or LineSpec.
    - Never leaked into annotation JSON.
    - Holds no global state.
    """

    def __init__(self, page_w: int, page_h: int, *, min_gap_px: int) -> None:
        self.page_w = int(page_w)
        self.page_h = int(page_h)
        self.min_gap_px = max(0, int(min_gap_px))
        self.rects: List[OccupancyRect] = []

    def add(self, rect: OccupancyRect) -> None:
        self.rects.append(rect)

    def fill_ratio(self) -> float:
        page_area = max(1, self.page_w * self.page_h)
        total = sum(rect.area for rect in self.rects)
        return min(1.0, float(total) / float(page_area))

    def _expanded(
        self,
        rect: OccupancyRect,
        gap: Optional[int] = None,
    ) -> Tuple[int, int, int, int]:
        actual_gap = self.min_gap_px if gap is None else max(0, int(gap))

        return (
            int(rect.x - actual_gap),
            int(rect.y - actual_gap),
            int(rect.x1 + actual_gap),
            int(rect.y1 + actual_gap),
        )

    @staticmethod
    def _intersects_box(
        a: Tuple[int, int, int, int],
        b: Tuple[int, int, int, int],
    ) -> bool:
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b

        return not (
            ax1 <= bx0
            or bx1 <= ax0
            or ay1 <= by0
            or by1 <= ay0
        )

    def overlaps(self, rect: OccupancyRect) -> bool:
        rect_box = self._expanded(rect)

        for other in self.rects:
            if self._intersects_box(rect_box, self._expanded(other, gap=0)):
                return True

        return False

    def min_center_distance(self, rect: OccupancyRect) -> float:
        if not self.rects:
            return float(max(self.page_w, self.page_h))

        cx, cy = rect.center
        best = float("inf")

        for other in self.rects:
            ox, oy = other.center
            dx = cx - ox
            dy = cy - oy
            distance = (dx * dx + dy * dy) ** 0.5

            if distance < best:
                best = distance

        return float(best)

    def score_candidate(
        self,
        rect: OccupancyRect,
        *,
        spread_percent: float,
        rng: random.Random,
    ) -> float:
        if rect.w <= 0 or rect.h <= 0:
            return -1e18

        if rect.x < 0 or rect.y < 0:
            return -1e18

        if rect.x1 > self.page_w or rect.y1 > self.page_h:
            return -1e18

        overlap_penalty = 0.0
        rect_box = self._expanded(rect)

        for other in self.rects:
            if self._intersects_box(rect_box, self._expanded(other, gap=0)):
                overlap_penalty += 10_000_000.0

        spread = max(0.0, min(100.0, float(spread_percent))) / 100.0
        distance_score = self.min_center_distance(rect) * spread

        edge_margin = min(
            rect.x,
            rect.y,
            self.page_w - rect.x1,
            self.page_h - rect.y1,
        )
        edge_score = max(0.0, float(edge_margin)) * 0.12
        jitter = rng.random() * 3.0

        return distance_score + edge_score + jitter - overlap_penalty


def occupancy_cfg(layout_cfg: Dict[str, object]) -> Dict[str, object]:
    raw = layout_cfg.get("occupancy", {}) or {}

    if not isinstance(raw, dict):
        raw = {}

    return {
        "enable": bool(raw.get("enable", True)),
        "whitespace_strategy": str(raw.get("whitespace_strategy", "balanced")),
        "spread_percent": float(raw.get("spread_percent", 65.0)),
        "min_gap_px": int(raw.get("min_gap_px", 12)),
        "max_place_attempts": int(raw.get("max_place_attempts", 48)),
        "target_fill_ratio": raw.get("target_fill_ratio", {}) or {},
    }


def target_fill_ratio_for_density(
    density_level: str,
    occ_cfg: Dict[str, object],
    rng: random.Random,
) -> float:
    default_map: Dict[str, Tuple[float, float]] = {
        "sparse": (0.06, 0.14),
        "normal": (0.14, 0.26),
        "dense": (0.26, 0.42),
        "mixed": (0.12, 0.34),
    }

    raw_map = occ_cfg.get("target_fill_ratio", {}) or {}
    pair = default_map.get(str(density_level), default_map["normal"])

    if isinstance(raw_map, dict):
        raw_pair = raw_map.get(str(density_level), None)

        if isinstance(raw_pair, (list, tuple)) and len(raw_pair) >= 2:
            try:
                pair = (float(raw_pair[0]), float(raw_pair[1]))
            except Exception:
                pass

    lo = max(0.01, min(0.95, float(pair[0])))
    hi = max(lo, min(0.95, float(pair[1])))

    return rng.uniform(lo, hi)


def strategy_scale_limits(strategy: str) -> Tuple[float, float]:
    strategy = str(strategy or "balanced").strip().lower()

    if strategy == "airy":
        return 0.72, 1.06

    if strategy == "compact":
        return 0.88, 1.34

    if strategy == "packed":
        return 0.96, 1.58

    return 0.80, 1.20


def scale_rect_size_to_fill_target(
    *,
    bw: int,
    bh: int,
    current_fill: float,
    target_fill: float,
    strategy: str,
) -> Tuple[int, int]:
    bw = max(1, int(bw))
    bh = max(1, int(bh))

    if current_fill <= 1e-6 or target_fill <= 1e-6:
        return bw, bh

    raw_scale = (target_fill / max(1e-6, current_fill)) ** 0.5
    lo, hi = strategy_scale_limits(strategy)
    scale = max(lo, min(hi, raw_scale))

    return (
        max(8, int(round(bw * scale))),
        max(8, int(round(bh * scale))),
    )


def sample_candidate_xy(
    *,
    rng: random.Random,
    page_w: int,
    page_h: int,
    margin_x: int,
    margin_y: int,
    bw: int,
    bh: int,
    full_width: bool,
) -> Tuple[int, int]:
    x_min = int(margin_x)
    y_min = int(margin_y)
    x_max = max(x_min, int(page_w - margin_x - bw))
    y_max = max(y_min, int(page_h - margin_y - bh))

    if full_width:
        x = x_min
    else:
        x = rng.randint(x_min, x_max) if x_max > x_min else x_min

    y = rng.randint(y_min, y_max) if y_max > y_min else y_min

    return int(x), int(y)


def refine_block_positions_with_occupancy(
    placed: List[PlacedBlock],
    *,
    w: int,
    h: int,
    density_level: str,
    layout_cfg: Dict[str, object],
    rng: random.Random,
) -> List[PlacedBlock]:
    """
    Refine block placement with a page-local occupancy model.

    This function:
    - makes spacing more natural,
    - scales total occupied area by density,
    - avoids writing occupancy debug state into PageSpec or JSON.
    """
    occ_cfg = occupancy_cfg(layout_cfg)

    if not bool(occ_cfg.get("enable", True)):
        return placed

    if not placed:
        return placed

    strategy = str(occ_cfg.get("whitespace_strategy", "balanced")).strip().lower()
    spread_percent = float(occ_cfg.get("spread_percent", 65.0))
    min_gap_px = int(occ_cfg.get("min_gap_px", 12))
    max_attempts = max(4, int(occ_cfg.get("max_place_attempts", 48)))

    if strategy == "airy":
        min_gap_px = int(min_gap_px * 1.50)
        spread_percent = max(spread_percent, 75.0)

    elif strategy == "compact":
        min_gap_px = int(min_gap_px * 0.80)
        spread_percent = max(35.0, min(spread_percent, 70.0))

    elif strategy == "packed":
        min_gap_px = int(min_gap_px * 0.55)
        spread_percent = max(20.0, min(spread_percent, 55.0))

    margin_x = int(0.08 * w)
    margin_y = int(0.08 * h)
    usable_w = max(1, w - 2 * margin_x)
    usable_h = max(1, h - 2 * margin_y)

    page_area = max(1, w * h)
    current_area = sum(
        max(1, int(item[3])) * max(1, int(item[4]))
        for item in placed
    )
    current_fill = min(1.0, float(current_area) / float(page_area))
    target_fill = target_fill_ratio_for_density(density_level, occ_cfg, rng)

    occ = PageOccupancy(w, h, min_gap_px=min_gap_px)
    refined: List[PlacedBlock] = []

    ordered = sorted(
        enumerate(placed),
        key=lambda pair: int(pair[1][3]) * int(pair[1][4]),
        reverse=True,
    )

    temp_out: Dict[int, PlacedBlock] = {}

    for original_idx, item in ordered:
        col, x, y, bw, bh, block_type, style = item
        style2 = dict(style)

        full_width = (
            bool(style2.get("full_width", False))
            or int(col) == -1
            or str(block_type) == "title"
        )

        new_bw, new_bh = scale_rect_size_to_fill_target(
            bw=int(bw),
            bh=int(bh),
            current_fill=current_fill,
            target_fill=target_fill,
            strategy=strategy,
        )

        if full_width:
            new_bw = usable_w
        else:
            new_bw = min(new_bw, usable_w)

        new_bh = min(new_bh, max(24, usable_h))

        best_score = -1e18
        best_rect: Optional[OccupancyRect] = None

        candidate_positions: List[Tuple[int, int]] = [
            (
                max(margin_x, min(int(x), w - margin_x - new_bw)),
                max(margin_y, min(int(y), h - margin_y - new_bh)),
            )
        ]

        for _ in range(max_attempts):
            candidate_positions.append(
                sample_candidate_xy(
                    rng=rng,
                    page_w=w,
                    page_h=h,
                    margin_x=margin_x,
                    margin_y=margin_y,
                    bw=new_bw,
                    bh=new_bh,
                    full_width=full_width,
                )
            )

        for cx, cy in candidate_positions:
            rect = OccupancyRect(
                x=int(cx),
                y=int(cy),
                w=int(new_bw),
                h=int(new_bh),
                kind=str(block_type),
            )
            score = occ.score_candidate(
                rect,
                spread_percent=spread_percent,
                rng=rng,
            )

            if score > best_score:
                best_score = score
                best_rect = rect

        if best_rect is None:
            best_rect = OccupancyRect(
                x=int(x),
                y=int(y),
                w=int(bw),
                h=int(bh),
                kind=str(block_type),
            )

        if occ.overlaps(best_rect):
            fallback = OccupancyRect(
                x=max(margin_x, min(int(x), w - margin_x - int(bw))),
                y=max(margin_y, min(int(y), h - margin_y - int(bh))),
                w=int(bw),
                h=int(bh),
                kind=str(block_type),
            )

            if not occ.overlaps(fallback):
                best_rect = fallback

        occ.add(best_rect)

        new_col = int(col)

        if new_col != -1:
            new_col = 0 if best_rect.center[0] < (w / 2.0) else 1

        temp_out[original_idx] = (
            new_col,
            int(best_rect.x),
            int(best_rect.y),
            int(best_rect.w),
            int(best_rect.h),
            str(block_type),
            style2,
        )

    for idx in range(len(placed)):
        refined.append(temp_out[idx])

    return refined