# src/docsynthfab/gui/shared/override_utils.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# Shared override/config helpers for GUI layers.
# This module uses only the Python standard library.

from __future__ import annotations

import json
from typing import Any, Dict


def safe_json_loads(text: str, fallback: Any = None) -> Any:
    """Parse JSON text safely."""
    try:
        return json.loads(text)
    except Exception:
        return fallback


def merge_maps(*maps: Dict[str, Any]) -> Dict[str, Any]:
    """Merge flat override maps from left to right."""
    out: Dict[str, Any] = {}

    for m in maps:
        out.update(m or {})

    return out


def clamp_percent(value: Any, default: float = 50.0) -> float:
    """Clamp any numeric-like value to the 0-100 range."""
    try:
        x = float(value)
    except Exception:
        x = float(default)

    return max(0.0, min(100.0, x))


def normalize_content_mix(
    text_value: Any,
    table_value: Any,
    latex_value: Any,
) -> Dict[str, float]:
    """
    Normalize text/table/latex percentages.

    User-facing expectation:
    text + table + latex should equal 100.

    If the user enters invalid values such as 0/0/0, safe defaults are used.
    """
    text = clamp_percent(text_value, 60.0)
    table = clamp_percent(table_value, 25.0)
    latex = clamp_percent(latex_value, 15.0)

    total = text + table + latex

    if total <= 0:
        text, table, latex = 60.0, 25.0, 15.0
        total = 100.0

    return {
        "text": round((text / total) * 100.0, 4),
        "table": round((table / total) * 100.0, 4),
        "latex": round((latex / total) * 100.0, 4),
    }


def gap_percent_to_px(percent: Any) -> int:
    """
    Convert GUI block-gap percent to backend min_gap_px.

    0   -> 0 px
    50  -> 24 px
    100 -> 64 px
    """
    p = clamp_percent(percent, 20.0)

    if p <= 50.0:
        return int(round((p / 50.0) * 24.0))

    return int(round(24.0 + ((p - 50.0) / 50.0) * 40.0))


def placement_search_percent_to_attempts(percent: Any) -> int:
    """
    Convert GUI placement-search percent to backend max_place_attempts.

    Higher value means better whitespace search, with a small speed cost.
    """
    p = clamp_percent(percent, 45.0)
    return int(round(12 + (p / 100.0) * 84))


def spacing_percent_to_line_gap_scale(percent: Any) -> float:
    """
    Convert GUI spacing percent to layout.line_gap_random_scale.

    GUI: 0-100
    Backend: 0.0-3.0
    """
    p = clamp_percent(percent, 0.0)
    return round((p / 100.0) * 3.0, 4)


def normalize_text_table_mix(
    text_value: Any,
    table_value: Any,
) -> Dict[str, float]:
    """
    Normalize text/table percentages for the main generator.

    The main generator intentionally does not expose LaTeX.
    LaTeX is handled by the dedicated LaTeX Renderer page.
    """
    text = clamp_percent(text_value, 70.0)
    table = clamp_percent(table_value, 30.0)

    total = text + table

    if total <= 0:
        text, table = 70.0, 30.0
        total = 100.0

    return {
        "text": round((text / total) * 100.0, 4),
        "table": round((table / total) * 100.0, 4),
        "latex": 0.0,
    }


def font_size_profile_to_range(profile: Any) -> Dict[str, int]:
    """
    Convert a simple user-facing font size profile into backend min/max px.

    The backend samples actual font sizes between min/max using a distribution.
    """
    name = str(profile or "Balanced").strip().lower()

    if name in {"readable", "large", "easy"}:
        return {"min_px": 14, "max_px": 22}

    if name in {"small / hard", "small-hard", "small_hard", "hard", "dense"}:
        return {"min_px": 7, "max_px": 13}

    if name in {"compact", "small"}:
        return {"min_px": 8, "max_px": 14}

    # Balanced default.
    return {"min_px": 10, "max_px": 18}


def layout_randomness_percent_to_line_gap(percent: Any) -> Dict[str, Any]:
    """
    Convert a single 0-100 Layout randomness slider into line-gap policy.

    Default is controlled Gaussian:
    - not as mechanical as uniform
    - not too extreme
    - natural hybrid line spacing for generated document lines
    """
    p = clamp_percent(percent, 25.0)
    strength = p / 100.0

    min_scale = 0.92 - 0.12 * strength
    max_scale = 1.08 + 0.30 * strength
    std_ratio = 0.08 + 0.11 * strength

    return {
        "distribution": "gaussian",
        "randomness_percent": round(p, 4),
        "min_scale": round(min_scale, 4),
        "max_scale": round(max_scale, 4),
        "mean_ratio": 0.55,
        "std_ratio": round(std_ratio, 4),
        "exponential_lambda": 2.5,
    }

def layout_randomness_percent_to_occupancy(percent: Any) -> Dict[str, Any]:
    """
    Convert one simple Layout randomness slider to whitespace/placement controls.

    These are backend technical controls. The main GUI should not expose them
    individually; Advanced/raw YAML may override them.
    """
    p = clamp_percent(percent, 25.0)

    if p < 25:
        whitespace_strategy = "balanced"
        spread_percent = 45.0
        block_gap_percent = 28.0
        placement_percent = 35.0
    elif p < 60:
        whitespace_strategy = "balanced"
        spread_percent = 65.0
        block_gap_percent = 20.0
        placement_percent = 45.0
    elif p < 85:
        whitespace_strategy = "spread"
        spread_percent = 78.0
        block_gap_percent = 14.0
        placement_percent = 60.0
    else:
        whitespace_strategy = "spread"
        spread_percent = 92.0
        block_gap_percent = 8.0
        placement_percent = 78.0

    return {
        "whitespace_strategy": whitespace_strategy,
        "spread_percent": spread_percent,
        "min_gap_px": gap_percent_to_px(block_gap_percent),
        "max_place_attempts": placement_search_percent_to_attempts(placement_percent),
    }


def density_percent_to_dist(percent: Any) -> Dict[str, float]:
    """
    Convert user-friendly density percent to dist.density_dist.

    0   -> sparse-heavy
    50  -> normal-heavy
    100 -> dense/mixed-heavy
    """
    p = clamp_percent(percent, 50.0)

    if p <= 50.0:
        t = p / 50.0

        sparse = 0.90 + (0.15 - 0.90) * t
        normal = 0.10 + (0.70 - 0.10) * t
        dense = 0.00 + (0.15 - 0.00) * t
        mixed = 0.00

    else:
        t = (p - 50.0) / 50.0

        sparse = 0.15 + (0.05 - 0.15) * t
        normal = 0.70 + (0.15 - 0.70) * t
        dense = 0.15 + (0.60 - 0.15) * t
        mixed = 0.00 + (0.20 - 0.00) * t

    total = sparse + normal + dense + mixed

    if total <= 0:
        return {
            "sparse": 0.20,
            "normal": 0.60,
            "dense": 0.20,
            "mixed": 0.00,
        }

    return {
        "sparse": round(sparse / total, 4),
        "normal": round(normal / total, 4),
        "dense": round(dense / total, 4),
        "mixed": round(mixed / total, 4),
    }


def content_mix_preview_label(mix: Dict[str, float]) -> str:
    """Return a human-readable content mix label."""
    text = float(mix.get("text", 0.0))
    table = float(mix.get("table", 0.0))
    latex = float(mix.get("latex", 0.0))

    if latex > 0:
        return f"Text {text:.0f}% / Table {table:.0f}% / LaTeX {latex:.0f}%"

    if table >= 99.9:
        return "Table only"

    if text >= 99.9:
        return "Text only"

    return f"Text {text:.0f}% / Table {table:.0f}%"



def table_amount_preview_label(mix: Dict[str, float]) -> str:
    """Return a human-readable table amount label."""
    table = float(mix.get("table", 0.0))

    if table <= 0:
        return "No tables"

    if table < 20:
        return "Some tables"

    if table < 60:
        return "Many tables"

    return "Table-heavy"


def density_preview_label(percent: Any) -> str:
    """Return Low/Medium/High label for user-facing density."""
    p = clamp_percent(percent, 50.0)

    if p < 25:
        return "Low"

    if p > 75:
        return "High"

    return "Medium"


def nested_from_flat_overrides(flat: Dict[str, Any]) -> Dict[str, Any]:
    """Convert flat dotted override keys to a nested dict."""
    out: Dict[str, Any] = {}

    for key, value in flat.items():
        cur = out
        parts = str(key).split(".")

        for part in parts[:-1]:
            nxt = cur.get(part)

            if not isinstance(nxt, dict):
                nxt = {}
                cur[part] = nxt

            cur = nxt

        cur[parts[-1]] = value

    return out


def lookup_nested_value(
    d: Dict[str, Any],
    path: str,
    default: Any = None,
) -> Any:
    """Read a dotted path from a nested dictionary."""
    cur: Any = d

    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default

        cur = cur[part]

    return cur


def negative_space_profile_to_occupancy(profile: object) -> dict:
    name = str(profile or "Controlled").strip().lower()

    if name in {"airy", "open", "loose"}:
        return {
            "whitespace_strategy": "airy",
            "spread_percent": 88.0,
            "min_gap_px": 16,
            "max_place_attempts": 128,
            "target_fill_ratio": {
                "sparse": [0.08, 0.16],
                "normal": [0.16, 0.30],
                "dense": [0.30, 0.46],
                "mixed": [0.18, 0.38],
            },
        }

    if name in {"dense controlled", "dense", "compact"}:
        return {
            "whitespace_strategy": "compact",
            "spread_percent": 60.0,
            "min_gap_px": 7,
            "max_place_attempts": 160,
            "target_fill_ratio": {
                "sparse": [0.16, 0.26],
                "normal": [0.32, 0.48],
                "dense": [0.46, 0.64],
                "mixed": [0.34, 0.56],
            },
        }

    return {
        "whitespace_strategy": "balanced",
        "spread_percent": 74.0,
        "min_gap_px": 10,
        "max_place_attempts": 180,
        "target_fill_ratio": {
            "sparse": [0.16, 0.28],
            "normal": [0.32, 0.48],
            "dense": [0.48, 0.66],
            "mixed": [0.36, 0.58],
        },
    }


def negative_space_profile_to_density_dist(density_percent: object, profile: object) -> dict:
    base = density_percent_to_dist(density_percent)
    name = str(profile or "Controlled").strip().lower()
    out = dict(base)

    if name in {"controlled", "dense controlled", "dense", "compact"}:
        out["sparse"] = min(float(out.get("sparse", 0.0)), 0.03)
        out["normal"] = max(float(out.get("normal", 0.0)), 0.30)
        out["dense"] = max(float(out.get("dense", 0.0)), 0.45)
    elif name in {"balanced", "normal"}:
        out["sparse"] = min(float(out.get("sparse", 0.0)), 0.08)

    total = sum(float(v) for v in out.values())
    if total <= 0:
        return {"sparse": 0.03, "normal": 0.35, "dense": 0.52, "mixed": 0.10}

    return {key: round(float(value) / total, 4) for key, value in out.items()}


def negative_space_profile_to_layout_targets(profile: object) -> dict:
    name = str(profile or "Controlled").strip().lower()

    if name in {"airy", "open", "loose"}:
        return {
            "sparse": {"line_count_range": [10, 26], "block_count_range": [3, 7]},
            "normal": {"line_count_range": [24, 56], "block_count_range": [6, 12]},
            "dense": {"line_count_range": [50, 95], "block_count_range": [10, 18]},
            "mixed": {"line_count_range": [28, 80], "block_count_range": [7, 16]},
        }

    if name in {"dense controlled", "dense", "compact"}:
        return {
            "sparse": {"line_count_range": [22, 42], "block_count_range": [5, 10]},
            "normal": {"line_count_range": [45, 85], "block_count_range": [9, 17]},
            "dense": {"line_count_range": [80, 135], "block_count_range": [14, 26]},
            "mixed": {"line_count_range": [55, 115], "block_count_range": [11, 22]},
        }

    return {
        "sparse": {"line_count_range": [22, 42], "block_count_range": [5, 9]},
        "normal": {"line_count_range": [44, 82], "block_count_range": [8, 15]},
        "dense": {"line_count_range": [72, 122], "block_count_range": [12, 22]},
        "mixed": {"line_count_range": [52, 102], "block_count_range": [9, 18]},
    }


def negative_space_profile_to_qc_overrides(profile: object) -> dict:
    name = str(profile or "Controlled").strip().lower()

    hard_rules = {
        # These are quality defects, not style differences.
        # They should stay strict even when the page is intentionally airy.
        "qc.reject_tofu_text_chars": True,
        "qc.require_content_purity_contract": True,
        "qc.require_global_line_order_contiguous": True,
        "qc.mask_binary_required": True,
        "qc.overlap_text_over_math_max_ratio": 0.01,

        # These keys are forward-compatible with the next validator patch.
        "qc.reject_code_token_leakage": True,
        "qc.max_code_token_leak_count": 0,
        "qc.reject_solid_black_regions": True,
        "qc.max_solid_black_region_count": 0,
    }

    if name in {"airy", "open", "loose"}:
        soft_rules = {
            "qc.profile": "airy",
            "qc.visual_coverage.enable": True,
            "qc.visual_coverage.min_content_ratio_by_density": {
                "sparse": 0.00025,
                "normal": 0.00055,
                "dense": 0.00090,
                "mixed": 0.00055,
            },
            "qc.visual_coverage.min_bbox_extent_ratio_by_density": {
                "sparse": 0.0030,
                "normal": 0.0065,
                "dense": 0.0100,
                "mixed": 0.0065,
            },
            "qc.density.density_soft_margin_abs": 0.0040,
            "qc.max_block_overlap_ratio_min_area": 0.28,
        }
        return {**soft_rules, **hard_rules}

    if name in {"dense controlled", "dense", "compact"}:
        soft_rules = {
            "qc.profile": "dense_controlled",
            "qc.visual_coverage.enable": True,
            "qc.visual_coverage.min_content_ratio_by_density": {
                "sparse": 0.00065,
                "normal": 0.00110,
                "dense": 0.00165,
                "mixed": 0.00110,
            },
            "qc.visual_coverage.min_bbox_extent_ratio_by_density": {
                "sparse": 0.0060,
                "normal": 0.0110,
                "dense": 0.0170,
                "mixed": 0.0110,
            },
            "qc.density.density_soft_margin_abs": 0.0025,
            "qc.max_block_overlap_ratio_min_area": 0.24,
        }
        return {**soft_rules, **hard_rules}

    soft_rules = {
        "qc.profile": "controlled",
        "qc.visual_coverage.enable": True,
        "qc.visual_coverage.min_content_ratio_by_density": {
            "sparse": 0.00045,
            "normal": 0.00085,
            "dense": 0.00125,
            "mixed": 0.00085,
        },
        "qc.visual_coverage.min_bbox_extent_ratio_by_density": {
            "sparse": 0.0045,
            "normal": 0.0085,
            "dense": 0.0130,
            "mixed": 0.0085,
        },
        "qc.density.density_soft_margin_abs": 0.0030,
        "qc.max_block_overlap_ratio_min_area": 0.26,
    }
    return {**soft_rules, **hard_rules}