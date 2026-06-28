# src/docsynthfab/qc/visual_quality.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import Any, Dict


def _minimum_visual_quality_thresholds(
    density_level: str,
    meta: Dict[str, Any],
    qc_cfg: Dict[str, Any],
) -> tuple[float, float]:
    """
    Return minimum visual-content and bbox-extent ratios.

    LaTeX can have naturally low ink coverage because it may contain thin
    strokes. For equation-heavy pages, bbox extent is often more reliable
    than raw pixel coverage.
    """
    visual_cfg = (qc_cfg.get("visual_coverage") or {}) if isinstance(qc_cfg, dict) else {}

    if not bool(visual_cfg.get("enable", True)):
        return 0.0, 0.0

    density_level = str(density_level or "normal")

    has_equation_layout = bool(meta.get("has_equation_layout", False))
    has_equation = bool(meta.get("has_equation", False))
    has_table = bool(meta.get("has_table", False))

    content_defaults = {
        "sparse": 0.00035,
        "normal": 0.00075,
        "dense": 0.00110,
        "mixed": 0.00075,
    }

    extent_defaults = {
        "sparse": 0.0040,
        "normal": 0.0080,
        "dense": 0.0120,
        "mixed": 0.0080,
    }

    min_content = float(
        (visual_cfg.get("min_content_ratio_by_density") or {}).get(
            density_level,
            content_defaults.get(density_level, content_defaults["normal"]),
        )
    )

    min_extent = float(
        (visual_cfg.get("min_bbox_extent_ratio_by_density") or {}).get(
            density_level,
            extent_defaults.get(density_level, extent_defaults["normal"]),
        )
    )

    if has_equation_layout or has_equation:
        min_content *= float(visual_cfg.get("equation_content_ratio_relax", 0.55))
        min_extent *= float(visual_cfg.get("equation_extent_ratio_relax", 0.90))

    if has_table:
        min_content *= float(visual_cfg.get("table_content_ratio_boost", 1.15))
        min_extent *= float(visual_cfg.get("table_extent_ratio_boost", 1.10))

    return max(0.0, min_content), max(0.0, min_extent)



