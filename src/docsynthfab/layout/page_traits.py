# src/docsynthfab/layout/page_traits.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import Dict

from .common import choice_dist


def default_page_family_dist() -> Dict[str, float]:
    """Default page-family distribution used when config does not override it."""
    return {
        "book": 0.34,
        "academic": 0.20,
        "report": 0.18,
        "worksheet": 0.14,
        "notes": 0.14,
    }


def default_family_layout_dist(page_family: str) -> Dict[str, float]:
    """Return the default layout-type distribution for a page family."""
    defaults: Dict[str, Dict[str, float]] = {
        "book": {"single_col": 0.74, "double_col": 0.20, "mixed_cols": 0.06},
        "academic": {"single_col": 0.10, "double_col": 0.78, "mixed_cols": 0.12},
        "report": {"single_col": 0.56, "double_col": 0.28, "mixed_cols": 0.16},
        "worksheet": {"single_col": 0.68, "double_col": 0.18, "mixed_cols": 0.14},
        "notes": {"single_col": 0.76, "double_col": 0.12, "mixed_cols": 0.12},
    }

    return defaults.get(page_family, defaults["report"])


def sample_page_family(cfg, rng: random.Random) -> str:
    """Sample the high-level page family."""
    layout_cfg = cfg.raw.get("layout", {}) or {}
    family_dist = layout_cfg.get("page_family_dist", default_page_family_dist())

    return choice_dist(rng, family_dist, default="report")


def sample_layout_type(cfg, rng: random.Random, page_family: str) -> str:
    """Sample the layout type for a page family."""
    layout_cfg = cfg.raw.get("layout", {}) or {}
    family_map = layout_cfg.get("family_layout_type_dist", {}) or {}
    family_dist = family_map.get(page_family, default_family_layout_dist(page_family))

    return choice_dist(rng, family_dist, default="single_col")


def sample_page_size(cfg, rng: random.Random) -> str:
    """Sample or resolve the configured page size key."""
    page_cfg = cfg.raw.get("page", {}) or {}
    size_dist = page_cfg.get("size_dist", None)

    if isinstance(size_dist, dict) and size_dist:
        return choice_dist(rng, size_dist, default="a4_portrait")

    size_name = str(page_cfg.get("size_name", "A4")).strip().upper()

    if size_name == "A4":
        return "a4_portrait"

    if size_name == "LETTER":
        return "letter_portrait"

    if size_name == "LEGAL":
        return "legal_portrait"

    return "a4_portrait"



