# src/docsynthfab/render/font_size.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import Any, Mapping


def _get_nested(mapping: Mapping[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = mapping

    for part in path.split("."):
        if not isinstance(cur, Mapping):
            return default

        if part not in cur:
            return default

        cur = cur[part]

    return cur


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def font_size_config(cfg: Any) -> Mapping[str, Any]:
    """
    Return render.text.font_size config.

    Accepts either:
    - raw config dict
    - AppConfig-like object with .raw
    """
    raw = getattr(cfg, "raw", cfg)

    if not isinstance(raw, Mapping):
        return {}

    value = _get_nested(raw, "render.text.font_size", {})

    return value if isinstance(value, Mapping) else {}


def sample_font_size_px(
    rng: random.Random,
    cfg: Any,
    *,
    default_min: int = 10,
    default_max: int = 18,
) -> int:
    """
    Sample a font size in pixels from render.text.font_size.

    Supported distributions:
    - gaussian: truncated Gaussian inside min/max
    - uniform: integer uniform inside min/max

    The function is deterministic when the caller provides a seeded rng.
    """
    size_cfg = font_size_config(cfg)

    min_px = _as_int(size_cfg.get("min_px"), default_min)
    max_px = _as_int(size_cfg.get("max_px"), default_max)

    if min_px > max_px:
        min_px, max_px = max_px, min_px

    min_px = max(4, min_px)
    max_px = max(min_px, max_px)

    distribution = str(size_cfg.get("distribution", "gaussian")).strip().lower()

    if distribution == "uniform":
        return int(rng.randint(min_px, max_px))

    mean_ratio = _as_float(size_cfg.get("mean_ratio"), 0.55)
    std_ratio = _as_float(size_cfg.get("std_ratio"), 0.18)

    mean_ratio = _clamp(mean_ratio, 0.0, 1.0)
    std_ratio = _clamp(std_ratio, 0.01, 1.0)

    span = max_px - min_px

    if span <= 0:
        return int(min_px)

    mean = min_px + span * mean_ratio
    std = max(1.0, span * std_ratio)

    for _ in range(24):
        value = rng.gauss(mean, std)

        if min_px <= value <= max_px:
            return int(round(value))

    # Safe fallback if repeated samples fall outside the truncated interval.
    return int(round(_clamp(mean, min_px, max_px)))



