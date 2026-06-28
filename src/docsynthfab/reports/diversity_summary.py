# src/docsynthfab/reports/diversity_summary.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# This module uses only the Python standard library.

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean, pstdev, pvariance
from typing import Any, Dict, List, Tuple

from .io_utils import _now_utc_iso, _safe_float
from .recommendations import build_recommendations


def _numeric_summary(values: List[float]) -> Dict[str, Any]:
    """Summarize numeric values with variance and simple quantiles."""
    clean = [
        float(v)
        for v in values
        if isinstance(v, (int, float)) and math.isfinite(float(v))
    ]

    if not clean:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "variance": None,
            "min": None,
            "max": None,
            "p05": None,
            "p50": None,
            "p95": None,
        }

    s = sorted(clean)

    def q(prob: float) -> float:
        if len(s) == 1:
            return s[0]

        pos = prob * (len(s) - 1)
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))

        if lo == hi:
            return s[lo]

        frac = pos - lo
        return s[lo] * (1.0 - frac) + s[hi] * frac

    return {
        "count": len(clean),
        "mean": mean(clean),
        "std": pstdev(clean) if len(clean) > 1 else 0.0,
        "variance": pvariance(clean) if len(clean) > 1 else 0.0,
        "min": s[0],
        "max": s[-1],
        "p05": q(0.05),
        "p50": q(0.50),
        "p95": q(0.95),
    }


def _entropy_from_counts(counts: Dict[str, int]) -> float:
    """Compute entropy in bits from category counts."""
    total = sum(int(v) for v in counts.values())

    if total <= 0:
        return 0.0

    ent = 0.0

    for v in counts.values():
        p = int(v) / total

        if p > 0:
            ent -= p * math.log2(p)

    return ent


def _categorical_summary(rows: List[Dict[str, Any]], field: str) -> Dict[str, Any]:
    """Summarize one categorical field."""
    counts: Counter[str] = Counter(str(r.get(field, "unknown")) for r in rows)
    total = sum(counts.values())
    dist = {k: v / total for k, v in counts.items()} if total else {}

    return {
        "field": field,
        "count": total,
        "unique": len(counts),
        "entropy_bits": _entropy_from_counts(dict(counts)),
        "counts": dict(counts),
        "distribution": dist,
    }


def _joint_coverage(rows: List[Dict[str, Any]], fields: Tuple[str, ...]) -> Dict[str, Any]:
    """Summarize joint category coverage for multiple fields."""
    counts: Counter[str] = Counter()

    for r in rows:
        key = " × ".join(str(r.get(f, "unknown")) for f in fields)
        counts[key] += 1

    return {
        "fields": list(fields),
        "unique_combinations": len(counts),
        "top_combinations": dict(counts.most_common(20)),
        "entropy_bits": _entropy_from_counts(dict(counts)),
    }


def _try_get_target_distributions(cfg_raw: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """
    Read target distributions from common config locations.

    Missing target distributions are ignored silently because reports should
    remain usable across config versions.
    """
    out: Dict[str, Dict[str, float]] = {}

    dist = cfg_raw.get("dist", {}) or {}
    layout = cfg_raw.get("layout", {}) or {}
    page = cfg_raw.get("page", {}) or {}

    if isinstance(layout.get("layout_type_dist"), dict):
        out["layout_type"] = {
            str(k): float(v)
            for k, v in layout["layout_type_dist"].items()
        }

    if isinstance(dist.get("density_dist"), dict):
        out["density_level"] = {
            str(k): float(v)
            for k, v in dist["density_dist"].items()
        }

    if isinstance(dist.get("noise_level_dist"), dict):
        out["noise_level"] = {
            str(k): float(v)
            for k, v in dist["noise_level_dist"].items()
        }

    if isinstance(dist.get("scale_dist"), dict):
        out["scale_profile"] = {
            str(k): float(v)
            for k, v in dist["scale_dist"].items()
        }

    if isinstance(page.get("size_dist"), dict):
        out["page_size_name"] = {
            str(k): float(v)
            for k, v in page["size_dist"].items()
        }

    return out


def _target_vs_observed(
    rows: List[Dict[str, Any]],
    cfg_raw: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare configured target distributions with observed output distributions."""
    targets = _try_get_target_distributions(cfg_raw)
    result: Dict[str, Any] = {}

    for field, target_dist in targets.items():
        observed = _categorical_summary(rows, field).get("distribution", {})
        keys = sorted(set(target_dist.keys()) | set(observed.keys()))

        result[field] = {
            "target": target_dist,
            "observed": {k: observed.get(k, 0.0) for k in keys},
            "abs_gap": {
                k: abs(float(target_dist.get(k, 0.0)) - float(observed.get(k, 0.0)))
                for k in keys
            },
            "signed_gap": {
                k: float(observed.get(k, 0.0)) - float(target_dist.get(k, 0.0))
                for k in keys
            },
        }

    return result


def build_diversity_summary(
    rows: List[Dict[str, Any]],
    cfg_raw: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the full diversity summary object."""
    numeric_fields = [
        "line_count",
        "block_count",
        "math_line_count",
        "table_block_count",
        "equation_block_count",
        "figure_block_count",
        "text_mask_ratio",
        "math_mask_ratio",
        "table_area_ratio",
        "equation_area_ratio",
        "figure_area_ratio",
        "rotation_deg",
    ]

    categorical_fields = [
        "layout_type",
        "density_level",
        "noise_level",
        "scale_profile",
        "page_family",
        "dominant_script",
        "has_table",
        "has_equation",
        "has_figure",
        "fallback_used",
    ]

    joint_fields = [
        ("layout_type", "noise_level"),
        ("density_level", "has_table"),
        ("density_level", "has_equation"),
        ("layout_type", "has_table"),
        ("has_table", "has_equation"),
        ("dominant_script", "has_equation"),
    ]

    numeric = {
        field: _numeric_summary([_safe_float(r.get(field), 0.0) for r in rows])
        for field in numeric_fields
    }

    categorical = {
        field: _categorical_summary(rows, field)
        for field in categorical_fields
    }

    joint = {
        " × ".join(fields): _joint_coverage(rows, fields)
        for fields in joint_fields
    }

    target_gap = _target_vs_observed(rows, cfg_raw)

    return {
        "version": "diversity-summary-v1",
        "created_at": _now_utc_iso(),
        "page_count": len(rows),
        "numeric": numeric,
        "categorical": categorical,
        "joint_coverage": joint,
        "target_vs_observed": target_gap,
        "recommendations": build_recommendations(numeric, categorical, target_gap),
    }


def write_diversity_summary_csv(path: Path, summary: Dict[str, Any]) -> None:
    """Write numeric and categorical diversity summaries as CSV."""
    rows: List[Dict[str, Any]] = []

    for field, s in summary.get("numeric", {}).items():
        row = {"kind": "numeric", "field": field}
        row.update(s)
        rows.append(row)

    for field, s in summary.get("categorical", {}).items():
        rows.append(
            {
                "kind": "categorical",
                "field": field,
                "count": s.get("count"),
                "unique": s.get("unique"),
                "entropy_bits": s.get("entropy_bits"),
                "counts_json": json.dumps(
                    s.get("counts", {}),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )

    fieldnames: List[str] = []
    seen = set()

    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)



