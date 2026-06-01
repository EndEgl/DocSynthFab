# src/ai1_gen/layout/common.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import Dict, Tuple


def choice_dist(
    rng: random.Random,
    dist: Dict[str, float],
    default: str = "normal",
) -> str:
    """Sample one string key from a weighted distribution."""
    if not isinstance(dist, dict) or not dist:
        return default

    items = [(str(key), max(0.0, float(value))) for key, value in dist.items()]
    total = sum(value for _, value in items)

    if total <= 0:
        return default

    pick = rng.random() * total
    acc = 0.0

    for key, prob in items:
        acc += prob
        if pick <= acc:
            return key

    return items[-1][0]


def rand_range(rng: random.Random, a: int, b: int) -> int:
    """Return a safe inclusive random integer range."""
    if b <= a:
        return int(a)

    return rng.randint(int(a), int(b))


def clamp(value: int, lo: int, hi: int) -> int:
    """Clamp an integer value into [lo, hi]."""
    return max(lo, min(hi, value))


def page_size_meta(size_key: str, dpi: int) -> Tuple[int, int, float, float, str]:
    """Return pixel size, inch size, and orientation for a supported page size."""
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

    width_in, height_in = size_map_in.get(size_key, size_map_in["a4_portrait"])
    width_px = int(round(width_in * dpi))
    height_px = int(round(height_in * dpi))
    orientation = "landscape" if width_in > height_in else "portrait"

    return width_px, height_px, width_in, height_in, orientation