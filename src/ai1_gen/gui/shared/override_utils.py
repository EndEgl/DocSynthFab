# src/ai1_gen/gui/shared/override_utils.py
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

    if table >= 99.9:
        return "Table only"

    if latex >= 99.9:
        return "LaTeX only"

    if text >= 99.9:
        return "Text only"

    return f"Text {text:.0f}% / Table {table:.0f}% / LaTeX {latex:.0f}%"


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