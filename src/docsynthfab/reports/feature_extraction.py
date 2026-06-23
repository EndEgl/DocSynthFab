# src/docsynthfab/reports/feature_extraction.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# This module uses only the Python standard library.

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .io_utils import (
    _bbox_area_xywh,
    _bool_int,
    _read_json,
    _safe_float,
    _safe_int,
)


def _dominant_script_and_counts(ann: Dict[str, Any]) -> Tuple[str, Dict[str, int]]:
    """Return the dominant gt_script value and the full script histogram."""
    counter: Counter[str] = Counter()

    for ln in ann.get("lines", []) or []:
        script = str(ln.get("gt_script", "unknown") or "unknown")
        counter[script] += 1

    if not counter:
        return "unknown", {}

    return counter.most_common(1)[0][0], dict(counter)


def _aug_ops(meta: Dict[str, Any]) -> str:
    """Flatten augmentation trace operation names into a comma-separated string."""
    trace = meta.get("aug_trace", []) or []
    ops: List[str] = []

    for item in trace:
        if isinstance(item, dict) and item.get("op"):
            ops.append(str(item["op"]))

    return ",".join(ops)


def extract_feature_row(ann: Dict[str, Any]) -> Dict[str, Any]:
    """Extract one flat feature row from one annotation JSON object."""
    meta = ann.get("meta", {}) or {}
    size = ann.get("size", {}) or {}
    lines = ann.get("lines", []) or []
    blocks = ann.get("blocks", []) or []

    page_w = _safe_int(size.get("w"), 0)
    page_h = _safe_int(size.get("h"), 0)
    page_area = max(1, page_w * page_h)

    line_count = len(lines)
    block_count = len(blocks)

    math_line_count = sum(1 for ln in lines if str(ln.get("line_type", "")) == "math")
    table_block_count = sum(1 for b in blocks if str(b.get("block_type", "")) == "table")
    equation_block_count = sum(1 for b in blocks if str(b.get("block_type", "")) == "equation")
    figure_block_count = sum(1 for b in blocks if str(b.get("block_type", "")) == "figure")

    table_area = sum(
        _bbox_area_xywh(b.get("bbox"))
        for b in blocks
        if str(b.get("block_type", "")) == "table"
    )
    equation_area = sum(
        _bbox_area_xywh(b.get("bbox"))
        for b in blocks
        if str(b.get("block_type", "")) == "equation"
    )
    figure_area = sum(
        _bbox_area_xywh(b.get("bbox"))
        for b in blocks
        if str(b.get("block_type", "")) == "figure"
    )

    dominant_script, script_counts = _dominant_script_and_counts(ann)

    text_mask_ratio = _safe_float(meta.get("mask_text_nonzero")) / page_area
    math_mask_ratio = _safe_float(meta.get("mask_math_nonzero")) / page_area

    return {
        "page_id": str(ann.get("page_id", "")),
        "layout_type": str(meta.get("layout_type", "unknown")),
        "density_level": str(meta.get("density_level", "unknown")),
        "noise_level": str(meta.get("noise_level", "unknown")),
        "scale_profile": str(meta.get("scale_profile", "unknown")),
        "page_family": str(meta.get("page_family", "unknown")),
        "page_w": page_w,
        "page_h": page_h,
        "page_area": page_area,
        "has_table": _bool_int(meta.get("has_table", False)),
        "has_equation": _bool_int(meta.get("has_equation", False)),
        "has_equation_layout": _bool_int(meta.get("has_equation_layout", False)),
        "has_figure": _bool_int(meta.get("has_figure", False)),
        "line_count": line_count,
        "block_count": block_count,
        "math_line_count": _safe_int(meta.get("math_line_count"), math_line_count),
        "table_block_count": _safe_int(meta.get("table_block_count"), table_block_count),
        "equation_block_count": _safe_int(meta.get("equation_block_count"), equation_block_count),
        "figure_block_count": _safe_int(meta.get("figure_block_count"), figure_block_count),
        "text_mask_ratio": text_mask_ratio,
        "math_mask_ratio": math_mask_ratio,
        "table_area_ratio": table_area / page_area,
        "equation_area_ratio": equation_area / page_area,
        "figure_area_ratio": figure_area / page_area,
        "rotation_deg": _safe_float(meta.get("rotation_deg"), 0.0),
        "perspective": _bool_int(meta.get("perspective", False)),
        "book_mode": _bool_int(meta.get("book_mode", False)),
        "fallback_used": _bool_int(meta.get("_fallback", False)),
        "dominant_script": dominant_script,
        "script_counts_json": json.dumps(script_counts, ensure_ascii=False, sort_keys=True),
        "aug_ops": _aug_ops(meta),
    }


def collect_feature_rows(ann_dir: Path) -> List[Dict[str, Any]]:
    """Collect feature rows from all annotation JSON files in ann_dir."""
    rows: List[Dict[str, Any]] = []

    for p in sorted(ann_dir.glob("*.json")):
        try:
            ann = _read_json(p)
            rows.append(extract_feature_row(ann))
        except Exception as e:
            rows.append(
                {
                    "page_id": p.stem,
                    "error": f"feature-extract-failed: {repr(e)}",
                }
            )

    return rows


def write_features(reports_dir: Path, rows: List[Dict[str, Any]]) -> None:
    """Write feature rows as both JSONL and CSV."""
    reports_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = reports_dir / "features.jsonl"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n")

    csv_path = reports_dir / "features.csv"

    fieldnames: List[str] = []
    seen = set()

    for row in rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow(row)



