# src/docsynthfab/layout/line_gap.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations


import random
from typing import Any, Mapping, Tuple


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def resolve_line_gap_policy(layout_cfg: Mapping[str, Any]) -> dict[str, Any]:
    """
    Resolve the new layout.line_gap policy.

    Backward compatibility:
    - If layout.line_gap is missing, use legacy layout.line_gap_random_scale.
    - The returned policy is consumed by _apply_line_gap_randomness(...).
    """
    raw_policy = layout_cfg.get("line_gap", {}) if isinstance(layout_cfg, Mapping) else {}

    if isinstance(raw_policy, Mapping) and raw_policy:
        randomness_percent = _as_float(raw_policy.get("randomness_percent"), 25.0)

        return {
            "distribution": str(raw_policy.get("distribution", "gaussian")).strip().lower(),
            "randomness_percent": _clamp(randomness_percent, 0.0, 100.0),
            "min_scale": _as_float(raw_policy.get("min_scale"), 0.85),
            "max_scale": _as_float(raw_policy.get("max_scale"), 1.35),
            "mean_ratio": _clamp(_as_float(raw_policy.get("mean_ratio"), 0.45), 0.0, 1.0),
            "std_ratio": _clamp(_as_float(raw_policy.get("std_ratio"), 0.18), 0.01, 1.0),
            "exponential_lambda": max(0.01, _as_float(raw_policy.get("exponential_lambda"), 2.5)),
        }

    legacy_scale = _as_float(layout_cfg.get("line_gap_random_scale", 0.0), 0.0)
    legacy_percent = _clamp((legacy_scale / 1.20) * 100.0, 0.0, 100.0)

    strength = legacy_percent / 100.0

    return {
        "distribution": "gaussian",
        "randomness_percent": legacy_percent,
        "min_scale": 1.0 - 0.35 * strength,
        "max_scale": 1.0 + 0.70 * strength,
        "mean_ratio": 0.45,
        "std_ratio": 0.08 + 0.22 * strength,
        "exponential_lambda": 2.5,
    }


def _sample_distribution_scale(
    *,
    policy: Mapping[str, Any],
    rng: random.Random,
) -> float:
    """
    Sample a positive line-gap multiplier from the configured policy.

    The result is centered around 1.0:
    - 1.0 means no change.
    - below 1.0 means slightly tighter.
    - above 1.0 means more open spacing.
    """
    distribution = str(policy.get("distribution", "gaussian")).strip().lower()

    randomness_percent = _clamp(
        _as_float(policy.get("randomness_percent"), 25.0),
        0.0,
        100.0,
    )

    if randomness_percent <= 0:
        return 1.0

    strength = randomness_percent / 100.0

    min_scale = _as_float(policy.get("min_scale"), 0.85)
    max_scale = _as_float(policy.get("max_scale"), 1.35)

    if min_scale > max_scale:
        min_scale, max_scale = max_scale, min_scale

    min_scale = max(0.10, min_scale)
    max_scale = max(min_scale, max_scale)

    if distribution == "uniform":
        return rng.uniform(min_scale, max_scale)

    if distribution == "exponential":
        lam = max(0.01, _as_float(policy.get("exponential_lambda"), 2.5))
        raw = rng.expovariate(lam)

        # Convert one-sided exponential noise into a bounded right tail.
        normalized = min(raw / max(1.0, 3.0 / lam), 1.0)
        value = 1.0 + (max_scale - 1.0) * normalized * strength
        return _clamp(value, min_scale, max_scale)

    if distribution == "lognormal":
        sigma = max(0.01, _as_float(policy.get("std_ratio"), 0.18)) * strength
        value = rng.lognormvariate(mu=0.0, sigma=sigma)
        return _clamp(value, min_scale, max_scale)

    # Default: truncated Gaussian.
    mean_ratio = _clamp(_as_float(policy.get("mean_ratio"), 0.45), 0.0, 1.0)
    std_ratio = _clamp(_as_float(policy.get("std_ratio"), 0.18), 0.01, 1.0)

    mean = min_scale + (max_scale - min_scale) * mean_ratio
    std = max(0.01, (max_scale - min_scale) * std_ratio * max(0.25, strength))

    for _ in range(24):
        value = rng.gauss(mean, std)

        if min_scale <= value <= max_scale:
            return float(value)

    return _clamp(mean, min_scale, max_scale)


def _policy_to_legacy_strength(policy: Mapping[str, Any]) -> float:
    """
    Convert the new line-gap policy to a legacy-like strength value.

    This lets the old damage-limiting logic remain useful while the actual
    variation comes from the new distribution policy.
    """
    randomness_percent = _clamp(
        _as_float(policy.get("randomness_percent"), 25.0),
        0.0,
        100.0,
    )

    return (randomness_percent / 100.0) * 1.20


def _apply_line_gap_randomness(
    bbox: Tuple[int, int, int, int],
    *,
    block_y: int,
    block_h: int,
    line_index: int,
    line_count: int,
    line_h: int,
    scale: float | None = None,
    policy: Mapping[str, Any] | None = None,
    density_level: str,
    block_type: str,
    rng: random.Random,
) -> Tuple[int, int, int, int]:
    """
    Apply controlled line-gap randomness inside a block.

    New behavior:
    - If policy is provided, sample variation from layout.line_gap.
    - If policy is missing, fall back to legacy scale behavior.

    Compatibility:
    - Existing callers can still pass scale only.
    """
    x, y, w, h = bbox

    if policy is not None:
        base_strength = _policy_to_legacy_strength(policy)
        sampled_scale = _sample_distribution_scale(policy=policy, rng=rng)
    else:
        base_strength = max(0.0, min(float(scale or 0.0), 3.0))
        sampled_scale = 1.0 + rng.uniform(-0.25, 1.0) * base_strength

    if base_strength <= 0:
        return bbox

    safe_scale = max(0.0, min(float(base_strength), 3.0))

    if density_level in {"dense", "very_dense"}:
        safe_scale *= 0.55

    elif density_level == "sparse":
        safe_scale *= 1.20

    if block_type == "title":
        safe_scale *= 0.20

    elif block_type == "caption":
        safe_scale *= 0.40

    elif block_type == "equation":
        safe_scale *= 0.30

    elif block_type == "list":
        safe_scale *= 0.70

    elif block_type == "table":
        safe_scale *= 0.0

    if safe_scale <= 0:
        return bbox

    if line_index == 0:
        safe_scale *= 0.35

    if line_count <= 2:
        safe_scale *= 0.45

    max_extra = int(max(0, line_h * 0.35 * safe_scale))

    if max_extra <= 0:
        return bbox

    # Direction and magnitude are controlled by sampled_scale.
    # sampled_scale < 1 can tighten, sampled_scale > 1 can open.
    centered = sampled_scale - 1.0

    if centered < 0:
        dy = -int(abs(centered) * max_extra)
    else:
        dy = int(centered * max_extra)

    # Add small local jitter so repeated lines do not look mechanical.
    jitter = rng.randint(-max(1, max_extra // 5), max(1, max_extra // 5))
    dy += jitter

    # Occasionally create a larger downward gap in high-randomness settings.
    if line_index > 0 and rng.random() < min(0.18 * safe_scale, 0.45):
        dy += rng.randint(0, max_extra)

    y2 = y + dy
    block_bottom = block_y + block_h
    y2 = max(block_y, min(y2, block_bottom - h))

    return int(x), int(y2), int(w), int(h)



