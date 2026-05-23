# src/ai1_gen/reports/dataset_reports.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
#
# Bu modül sadece stdlib kullanır.
# Amaç:
# - Üretim bittikten sonra reports/ klasörüne dataset contract + diversity raporu yazmak.
# - Generator çekirdeğini bozmadan metadata üzerinden ölçüm yapmak.

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev, pvariance
from typing import Any, Dict, Iterable, List, Optional, Tuple


LABEL_SCHEMA_VERSION = "document-ai-label-schema-v1"


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _bool_int(x: Any) -> int:
    return 1 if bool(x) else 0


def _bbox_area_xywh(bbox: Any) -> float:
    if not isinstance(bbox, list) or len(bbox) < 4:
        return 0.0
    return max(0.0, _safe_float(bbox[2])) * max(0.0, _safe_float(bbox[3]))


def build_label_schema() -> Dict[str, Any]:
    """
    İlk stabil schema.
    Şimdilik table cell ayrı class değil; table_region olarak tutulur.
    İkinci fazda table_cell_text eklenebilir.
    """
    classes = [
        {
            "id": 0,
            "name": "background",
            "semantic_type": "background",
            "ocr_target_type": "ignore",
            "mask_channel": 0,
            "description": "Pixels outside document content.",
            "recommended_tasks": ["segmentation"],
            "export_targets": ["segformer", "native"],
        },
        {
            "id": 1,
            "name": "plain_text",
            "semantic_type": "plain_text",
            "ocr_target_type": "plain_text",
            "mask_channel": 1,
            "description": "Normal text such as paragraphs, titles, captions, headers, or footers.",
            "recommended_tasks": ["segmentation", "layout_detection", "ocr_recognition"],
            "export_targets": ["segformer", "coco", "yolo", "trocr", "paddleocr", "native"],
        },
        {
            "id": 2,
            "name": "table_region",
            "semantic_type": "table_region",
            "ocr_target_type": "table_structure",
            "mask_channel": 2,
            "description": "Full table region. Cell-level export can be added in a later phase.",
            "recommended_tasks": ["segmentation", "layout_detection", "table_detection"],
            "export_targets": ["segformer", "coco", "yolo", "native"],
        },
        {
            "id": 3,
            "name": "math_latex",
            "semantic_type": "math_latex",
            "ocr_target_type": "latex_formula",
            "mask_channel": 3,
            "description": "Rendered math or LaTeX formula region.",
            "recommended_tasks": ["segmentation", "layout_detection", "latex_recognition"],
            "export_targets": ["segformer", "coco", "yolo", "latex_ocr", "native"],
        },
        {
            "id": 4,
            "name": "figure",
            "semantic_type": "figure",
            "ocr_target_type": "ignore",
            "mask_channel": 4,
            "description": "Non-text figure, drawing, chart, or decorative region.",
            "recommended_tasks": ["segmentation", "layout_detection"],
            "export_targets": ["segformer", "coco", "yolo", "native"],
        },
    ]

    return {
        "schema_version": LABEL_SCHEMA_VERSION,
        "task_family": "document_ai",
        "classes": classes,
        "mask_channels": {str(c["mask_channel"]): c["name"] for c in classes},
        "recommended_task_mapping": {
            "segmentation": ["background", "plain_text", "table_region", "math_latex", "figure"],
            "layout_detection": ["plain_text", "table_region", "math_latex", "figure"],
            "ocr_recognition": ["plain_text"],
            "latex_recognition": ["math_latex"],
            "table_detection": ["table_region"],
        },
        "notes": [
            "This schema describes generated labels, not a published dataset.",
            "The generator output can be exported to model-specific formats.",
            "table_cell_text is intentionally left for the next schema phase.",
        ],
    }


def label_schema_markdown(schema: Dict[str, Any]) -> str:
    lines = [
        "# Label Schema",
        "",
        f"- Schema version: `{schema.get('schema_version')}`",
        f"- Task family: `{schema.get('task_family')}`",
        "",
        "| ID | Name | Semantic type | OCR target | Mask channel | Recommended tasks |",
        "|---:|---|---|---|---:|---|",
    ]

    for c in schema.get("classes", []):
        lines.append(
            "| {id} | `{name}` | `{semantic}` | `{ocr}` | {ch} | {tasks} |".format(
                id=c.get("id"),
                name=c.get("name"),
                semantic=c.get("semantic_type"),
                ocr=c.get("ocr_target_type"),
                ch=c.get("mask_channel"),
                tasks=", ".join(c.get("recommended_tasks", [])),
            )
        )

    lines.extend(
        [
            "",
            "## Usage",
            "",
            "- Segmentation models should use `mask_channel` values.",
            "- OCR recognition exports should use `plain_text` lines and `gt_text`.",
            "- LaTeX recognition exports should use `math_latex` regions and `gt_latex`.",
            "- Table structure support starts with `table_region`; cell-level schema can be added later.",
        ]
    )
    return "\n".join(lines)


def _dominant_script_and_counts(ann: Dict[str, Any]) -> Tuple[str, Dict[str, int]]:
    counter: Counter[str] = Counter()
    for ln in ann.get("lines", []) or []:
        script = str(ln.get("gt_script", "unknown") or "unknown")
        counter[script] += 1
    if not counter:
        return "unknown", {}
    return counter.most_common(1)[0][0], dict(counter)


def _aug_ops(meta: Dict[str, Any]) -> str:
    trace = meta.get("aug_trace", []) or []
    ops: List[str] = []
    for item in trace:
        if isinstance(item, dict) and item.get("op"):
            ops.append(str(item["op"]))
    return ",".join(ops)


def extract_feature_row(ann: Dict[str, Any]) -> Dict[str, Any]:
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

    table_area = sum(_bbox_area_xywh(b.get("bbox")) for b in blocks if str(b.get("block_type", "")) == "table")
    equation_area = sum(_bbox_area_xywh(b.get("bbox")) for b in blocks if str(b.get("block_type", "")) == "equation")
    figure_area = sum(_bbox_area_xywh(b.get("bbox")) for b in blocks if str(b.get("block_type", "")) == "figure")

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


def _numeric_summary(values: List[float]) -> Dict[str, Any]:
    clean = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v))]
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
    Config'teki hedef dağılımları en yaygın yerlerden okur.
    Bulamazsa sessiz geçer.
    """
    out: Dict[str, Dict[str, float]] = {}

    dist = cfg_raw.get("dist", {}) or {}
    layout = cfg_raw.get("layout", {}) or {}
    page = cfg_raw.get("page", {}) or {}

    if isinstance(layout.get("layout_type_dist"), dict):
        out["layout_type"] = {str(k): float(v) for k, v in layout["layout_type_dist"].items()}

    if isinstance(dist.get("density_dist"), dict):
        out["density_level"] = {str(k): float(v) for k, v in dist["density_dist"].items()}

    if isinstance(dist.get("noise_level_dist"), dict):
        out["noise_level"] = {str(k): float(v) for k, v in dist["noise_level_dist"].items()}

    if isinstance(dist.get("scale_dist"), dict):
        out["scale_profile"] = {str(k): float(v) for k, v in dist["scale_dist"].items()}

    if isinstance(page.get("size_dist"), dict):
        out["page_size_name"] = {str(k): float(v) for k, v in page["size_dist"].items()}

    return out


def _target_vs_observed(
    rows: List[Dict[str, Any]],
    cfg_raw: Dict[str, Any],
) -> Dict[str, Any]:
    targets = _try_get_target_distributions(cfg_raw)
    result: Dict[str, Any] = {}

    for field, target_dist in targets.items():
        observed = _categorical_summary(rows, field).get("distribution", {})
        keys = sorted(set(target_dist.keys()) | set(observed.keys()))
        result[field] = {
            "target": target_dist,
            "observed": {k: observed.get(k, 0.0) for k in keys},
            "abs_gap": {k: abs(float(target_dist.get(k, 0.0)) - float(observed.get(k, 0.0))) for k in keys},
            "signed_gap": {k: float(observed.get(k, 0.0)) - float(target_dist.get(k, 0.0)) for k in keys},
        }

    return result


def build_diversity_summary(rows: List[Dict[str, Any]], cfg_raw: Dict[str, Any]) -> Dict[str, Any]:
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


def build_recommendations(
    numeric: Dict[str, Any],
    categorical: Dict[str, Any],
    target_gap: Dict[str, Any],
) -> List[Dict[str, str]]:
    recs: List[Dict[str, str]] = []

    has_table_dist = categorical.get("has_table", {}).get("distribution", {})
    table_ratio = float(has_table_dist.get("1", has_table_dist.get("True", 0.0)) or 0.0)
    if table_ratio < 0.10:
        recs.append(
            {
                "level": "warning",
                "area": "tables",
                "finding": f"Observed table page ratio is low: {table_ratio:.3f}.",
                "recommendation": "Increase content.has_table_prob and inspect table QC/layout failures.",
            }
        )

    has_eq_dist = categorical.get("has_equation", {}).get("distribution", {})
    eq_ratio = float(has_eq_dist.get("1", has_eq_dist.get("True", 0.0)) or 0.0)
    if eq_ratio < 0.10:
        recs.append(
            {
                "level": "info",
                "area": "latex",
                "finding": f"Observed equation page ratio is low: {eq_ratio:.3f}.",
                "recommendation": "Increase content.has_equation_prob or equation block placement diversity.",
            }
        )

    math_var = numeric.get("math_mask_ratio", {}).get("variance")
    if math_var is not None and float(math_var) < 1e-8:
        recs.append(
            {
                "level": "info",
                "area": "math_mask_variance",
                "finding": "math_mask_ratio variance is very low.",
                "recommendation": "Increase LaTeX expression size, equation count, or formula layout variation.",
            }
        )

    layout_entropy = categorical.get("layout_type", {}).get("entropy_bits")
    if layout_entropy is not None and float(layout_entropy) < 0.80:
        recs.append(
            {
                "level": "info",
                "area": "layout_diversity",
                "finding": f"layout_type entropy is low: {float(layout_entropy):.3f} bits.",
                "recommendation": "Balance layout.layout_type_dist or add more page families.",
            }
        )

    script_entropy = categorical.get("dominant_script", {}).get("entropy_bits")
    if script_entropy is not None and float(script_entropy) < 0.80:
        recs.append(
            {
                "level": "info",
                "area": "script_diversity",
                "finding": f"dominant_script entropy is low: {float(script_entropy):.3f} bits.",
                "recommendation": "Balance render.text.scripts_dist or add more multilingual content bank entries.",
            }
        )

    fallback_dist = categorical.get("fallback_used", {}).get("distribution", {})
    fallback_ratio = float(fallback_dist.get("1", fallback_dist.get("True", 0.0)) or 0.0)
    if fallback_ratio > 0.02:
        recs.append(
            {
                "level": "warning",
                "area": "fallback",
                "finding": f"Fallback ratio is {fallback_ratio:.3f}.",
                "recommendation": "QC or augmentation may be too aggressive. Inspect errors.jsonl and failed_pages.log.",
            }
        )

    for field, gap_obj in target_gap.items():
        signed = gap_obj.get("signed_gap", {})
        for k, gap in signed.items():
            if abs(float(gap)) >= 0.15:
                direction = "under-produced" if float(gap) < 0 else "over-produced"
                recs.append(
                    {
                        "level": "info",
                        "area": f"target_vs_observed:{field}",
                        "finding": f"`{k}` is {direction}; signed gap={float(gap):.3f}.",
                        "recommendation": f"Adjust the config distribution for `{field}` or inspect generation/QC constraints.",
                    }
                )

    if not recs:
        recs.append(
            {
                "level": "ok",
                "area": "overall",
                "finding": "No major diversity warnings were detected by the initial rules.",
                "recommendation": "Proceed to export and model benchmark.",
            }
        )

    return recs


def write_diversity_summary_csv(path: Path, summary: Dict[str, Any]) -> None:
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
                "counts_json": json.dumps(s.get("counts", {}), ensure_ascii=False, sort_keys=True),
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


def diversity_report_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# Diversity Report",
        "",
        f"- Created at: `{summary.get('created_at')}`",
        f"- Page count: `{summary.get('page_count')}`",
        "",
        "## Numeric variance summary",
        "",
        "| Field | Mean | Std | Variance | Min | P50 | P95 | Max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for field, s in summary.get("numeric", {}).items():
        lines.append(
            "| {field} | {mean} | {std} | {var} | {minv} | {p50} | {p95} | {maxv} |".format(
                field=field,
                mean=_fmt(s.get("mean")),
                std=_fmt(s.get("std")),
                var=_fmt(s.get("variance")),
                minv=_fmt(s.get("min")),
                p50=_fmt(s.get("p50")),
                p95=_fmt(s.get("p95")),
                maxv=_fmt(s.get("max")),
            )
        )

    lines.extend(
        [
            "",
            "## Categorical diversity",
            "",
            "| Field | Unique | Entropy bits | Top counts |",
            "|---|---:|---:|---|",
        ]
    )

    for field, s in summary.get("categorical", {}).items():
        counts = s.get("counts", {}) or {}
        top = dict(Counter(counts).most_common(6))
        lines.append(
            f"| {field} | {s.get('unique')} | {_fmt(s.get('entropy_bits'))} | `{json.dumps(top, ensure_ascii=False)}` |"
        )

    lines.extend(
        [
            "",
            "## Joint coverage",
            "",
            "| Fields | Unique combinations | Entropy bits | Top combinations |",
            "|---|---:|---:|---|",
        ]
    )

    for name, s in summary.get("joint_coverage", {}).items():
        top = s.get("top_combinations", {}) or {}
        lines.append(
            f"| {name} | {s.get('unique_combinations')} | {_fmt(s.get('entropy_bits'))} | `{json.dumps(top, ensure_ascii=False)}` |"
        )

    lines.extend(
        [
            "",
            "## Target vs observed gap",
            "",
        ]
    )

    gap = summary.get("target_vs_observed", {}) or {}
    if not gap:
        lines.append("No config target distributions were detected for comparison.")
    else:
        for field, obj in gap.items():
            lines.append(f"### `{field}`")
            lines.append("")
            lines.append("| Value | Target | Observed | Signed gap | Abs gap |")
            lines.append("|---|---:|---:|---:|---:|")
            target = obj.get("target", {}) or {}
            observed = obj.get("observed", {}) or {}
            signed = obj.get("signed_gap", {}) or {}
            abs_gap = obj.get("abs_gap", {}) or {}
            for k in sorted(set(target) | set(observed)):
                lines.append(
                    f"| `{k}` | {_fmt(target.get(k, 0.0))} | {_fmt(observed.get(k, 0.0))} | {_fmt(signed.get(k, 0.0))} | {_fmt(abs_gap.get(k, 0.0))} |"
                )
            lines.append("")

    lines.extend(
        [
            "",
            "## Recommendations",
            "",
            "| Level | Area | Finding | Recommendation |",
            "|---|---|---|---|",
        ]
    )

    for r in summary.get("recommendations", []) or []:
        lines.append(
            f"| {r.get('level')} | {r.get('area')} | {r.get('finding')} | {r.get('recommendation')} |"
        )

    return "\n".join(lines)


def _fmt(x: Any) -> str:
    if x is None:
        return ""
    try:
        return f"{float(x):.6g}"
    except Exception:
        return str(x)


def build_dataset_card(
    *,
    project_name: str,
    version: str,
    cfg_path: str,
    out_root: Path,
    pages_requested: int,
    pages_ok: int,
    pages_fail: int,
    seed: int,
    workers: int,
    splits: Dict[str, Any],
    export_targets: List[str],
) -> str:
    return "\n".join(
        [
            "# Generated Dataset Card",
            "",
            "## Generator",
            "",
            f"- Project: `{project_name}`",
            f"- Version: `{version}`",
            f"- Label schema: `{LABEL_SCHEMA_VERSION}`",
            f"- Created at: `{_now_utc_iso()}`",
            "",
            "## Run",
            "",
            f"- Config path: `{cfg_path}`",
            f"- Output root: `{out_root}`",
            f"- Pages requested: `{pages_requested}`",
            f"- Pages OK: `{pages_ok}`",
            f"- Pages failed: `{pages_fail}`",
            f"- Seed: `{seed}`",
            f"- Workers: `{workers}`",
            f"- Splits: `{json.dumps(splits, ensure_ascii=False)}`",
            f"- Export targets: `{', '.join(export_targets) if export_targets else 'native'}`",
            "",
            "## Output folders",
            "",
            "- `images/`: generated page images",
            "- `masks/`: generated segmentation masks",
            "- `ann/`: full annotation JSON files",
            "- `gt/`: ground-truth export JSON files",
            "- `splits/`: train/val/test page id lists",
            "- `reports/`: schema, run manifest, feature table, and diversity report",
            "- `exports/`: model-specific export packages",
            "",
            "## Recommended uses",
            "",
            "- Synthetic OCR and Document AI experiments",
            "- Text/table/math region segmentation",
            "- Layout detection",
            "- OCR line recognition after crop export",
            "- LaTeX/math region experiments",
            "",
            "## Not recommended uses",
            "",
            "- Claiming real-world OCR quality without real validation data",
            "- Replacing domain-specific evaluation",
            "- Treating synthetic diversity as automatically useful without benchmark checks",
        ]
    )


def write_run_manifest(
    path: Path,
    *,
    project_name: str,
    version: str,
    cfg_path: str,
    out_root: Path,
    pages_requested: int,
    pages_ok: int,
    pages_fail: int,
    seed: int,
    workers: int,
    splits: Dict[str, Any],
    export_targets: List[str],
    qc_summary: Dict[str, Any],
) -> Dict[str, Any]:
    manifest = {
        "manifest_version": "run-manifest-v1",
        "project_name": project_name,
        "generator_version": version,
        "label_schema_version": LABEL_SCHEMA_VERSION,
        "created_at": _now_utc_iso(),
        "config_path": cfg_path,
        "out_root": str(out_root),
        "pages_requested": pages_requested,
        "pages_ok": pages_ok,
        "pages_fail": pages_fail,
        "seed": seed,
        "workers": workers,
        "splits": splits,
        "export_targets": export_targets,
        "outputs": {
            "images": "images/",
            "masks": "masks/",
            "annotations": "ann/",
            "ground_truth": "gt/",
            "splits": "splits/",
            "reports": "reports/",
            "exports": "exports/",
        },
        "qc_summary": qc_summary,
    }
    _write_json(path, manifest)
    return manifest


def write_dataset_reports(
    *,
    out_root: Path,
    cfg_raw: Dict[str, Any],
    cfg_path: str,
    version: str,
    pages_requested: int,
    pages_ok: int,
    pages_fail: int,
    seed: int,
    workers: int,
    splits: Dict[str, Any],
    qc_summary: Dict[str, Any],
    project_name: str = "AI1 Gen",
    export_targets: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    CLI sonunda çağrılacak ana fonksiyon.
    Mevcut üretim output'una dokunmadan reports/ çıktıları üretir.
    """
    export_targets = export_targets or ["native"]
    out_root = Path(out_root)
    reports_dir = out_root / "reports"
    ann_dir = out_root / "ann"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (out_root / "exports").mkdir(parents=True, exist_ok=True)

    schema = build_label_schema()
    _write_json(reports_dir / "label_schema.json", schema)
    _write_text(reports_dir / "label_schema.md", label_schema_markdown(schema))

    manifest = write_run_manifest(
        reports_dir / "run_manifest.json",
        project_name=project_name,
        version=version,
        cfg_path=cfg_path,
        out_root=out_root,
        pages_requested=pages_requested,
        pages_ok=pages_ok,
        pages_fail=pages_fail,
        seed=seed,
        workers=workers,
        splits=splits,
        export_targets=export_targets,
        qc_summary=qc_summary,
    )

    card = build_dataset_card(
        project_name=project_name,
        version=version,
        cfg_path=cfg_path,
        out_root=out_root,
        pages_requested=pages_requested,
        pages_ok=pages_ok,
        pages_fail=pages_fail,
        seed=seed,
        workers=workers,
        splits=splits,
        export_targets=export_targets,
    )
    _write_text(reports_dir / "dataset_card.md", card)

    rows = collect_feature_rows(ann_dir)
    write_features(reports_dir, rows)

    summary = build_diversity_summary(rows, cfg_raw)
    _write_json(reports_dir / "diversity_summary.json", summary)
    write_diversity_summary_csv(reports_dir / "diversity_summary.csv", summary)
    _write_text(reports_dir / "diversity_report.md", diversity_report_markdown(summary))

    return {
        "reports_dir": str(reports_dir),
        "manifest": manifest,
        "page_count": len(rows),
        "diversity_summary": summary,
    }