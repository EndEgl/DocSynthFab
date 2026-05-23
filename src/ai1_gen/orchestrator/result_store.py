# src/ai1_gen/orchestrator/result_store.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .models import RunSummary


def _read_json_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def tail_text(path: str | Path, max_chars: int = 4000) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    txt = p.read_text(encoding="utf-8", errors="replace")
    if len(txt) <= max_chars:
        return txt
    return txt[-max_chars:]


def _safe_get_ratio_from_categorical(
    diversity: Dict[str, Any],
    field: str,
    positive_key: str = "1",
) -> Optional[float]:
    try:
        dist = (
            diversity.get("categorical", {})
            .get(field, {})
            .get("distribution", {})
        )
        if positive_key in dist:
            return float(dist[positive_key])
        if "True" in dist:
            return float(dist["True"])
        if "true" in dist:
            return float(dist["true"])
        return None
    except Exception:
        return None


def _safe_get_numeric_stat(
    diversity: Dict[str, Any],
    field: str,
    stat: str,
) -> Optional[float]:
    try:
        value = diversity.get("numeric", {}).get(field, {}).get(stat)
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _safe_get_entropy(
    diversity: Dict[str, Any],
    field: str,
) -> Optional[float]:
    try:
        value = diversity.get("categorical", {}).get(field, {}).get("entropy_bits")
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _build_diversity_dashboard(diversity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Web GUI / Desktop GUI için kısa, sayısal diversity özeti.
    Full veri yine reports/diversity_summary.json içinde durur.
    """
    if not diversity:
        return {}

    numeric = diversity.get("numeric", {}) or {}
    categorical = diversity.get("categorical", {}) or {}
    joint = diversity.get("joint_coverage", {}) or {}

    dashboard = {
        "page_count": diversity.get("page_count"),

        # İçerik oranları
        "has_table_ratio": _safe_get_ratio_from_categorical(diversity, "has_table"),
        "has_equation_ratio": _safe_get_ratio_from_categorical(diversity, "has_equation"),
        "has_figure_ratio": _safe_get_ratio_from_categorical(diversity, "has_figure"),
        "fallback_ratio": _safe_get_ratio_from_categorical(diversity, "fallback_used"),

        # Varyans metrikleri
        "line_count_variance": _safe_get_numeric_stat(diversity, "line_count", "variance"),
        "block_count_variance": _safe_get_numeric_stat(diversity, "block_count", "variance"),
        "text_mask_ratio_variance": _safe_get_numeric_stat(diversity, "text_mask_ratio", "variance"),
        "math_mask_ratio_variance": _safe_get_numeric_stat(diversity, "math_mask_ratio", "variance"),
        "table_area_ratio_variance": _safe_get_numeric_stat(diversity, "table_area_ratio", "variance"),
        "equation_area_ratio_variance": _safe_get_numeric_stat(diversity, "equation_area_ratio", "variance"),

        # Ortalama alan/yoğunluk
        "text_mask_ratio_mean": _safe_get_numeric_stat(diversity, "text_mask_ratio", "mean"),
        "math_mask_ratio_mean": _safe_get_numeric_stat(diversity, "math_mask_ratio", "mean"),
        "table_area_ratio_mean": _safe_get_numeric_stat(diversity, "table_area_ratio", "mean"),
        "equation_area_ratio_mean": _safe_get_numeric_stat(diversity, "equation_area_ratio", "mean"),

        # Entropy
        "layout_entropy_bits": _safe_get_entropy(diversity, "layout_type"),
        "density_entropy_bits": _safe_get_entropy(diversity, "density_level"),
        "noise_entropy_bits": _safe_get_entropy(diversity, "noise_level"),
        "script_entropy_bits": _safe_get_entropy(diversity, "dominant_script"),

        # Ham kısa objeler
        "numeric_fields": sorted(numeric.keys()),
        "categorical_fields": sorted(categorical.keys()),
        "joint_fields": sorted(joint.keys()),
    }

    return dashboard


def build_run_summary(run_id: str, out_root: str, state: str) -> RunSummary:
    out_dir = Path(out_root)

    qc_summary_path = out_dir / "qc_summary.json"
    run_log_path = out_dir / "run.log"
    gt_jsonl_path = out_dir / "gt_pages.jsonl"

    train_split_path = out_dir / "splits" / "train.txt"
    val_split_path = out_dir / "splits" / "val.txt"
    test_split_path = out_dir / "splits" / "test.txt"

    reports_dir = out_dir / "reports"
    exports_dir = out_dir / "exports"

    diversity_summary_path = reports_dir / "diversity_summary.json"
    diversity_report_path = reports_dir / "diversity_report.md"
    features_csv_path = reports_dir / "features.csv"
    features_jsonl_path = reports_dir / "features.jsonl"
    dataset_card_path = reports_dir / "dataset_card.md"
    run_manifest_path = reports_dir / "run_manifest.json"
    label_schema_path = reports_dir / "label_schema.json"

    export_summary_path = exports_dir / "export_summary.json"

    qc = _read_json_if_exists(qc_summary_path) or {}
    diversity = _read_json_if_exists(diversity_summary_path) or {}
    export_summary = _read_json_if_exists(export_summary_path) or {}

    diversity_dashboard = _build_diversity_dashboard(diversity)

    extra: Dict[str, Any] = {
        "qc": qc,
        "diversity": diversity,
        "diversity_dashboard": diversity_dashboard,
        "export_summary": export_summary,

        "reports_dir": str(reports_dir) if reports_dir.exists() else None,
        "exports_dir": str(exports_dir) if exports_dir.exists() else None,

        "diversity_summary_path": str(diversity_summary_path) if diversity_summary_path.exists() else None,
        "diversity_report_path": str(diversity_report_path) if diversity_report_path.exists() else None,
        "features_csv_path": str(features_csv_path) if features_csv_path.exists() else None,
        "features_jsonl_path": str(features_jsonl_path) if features_jsonl_path.exists() else None,
        "dataset_card_path": str(dataset_card_path) if dataset_card_path.exists() else None,
        "run_manifest_path": str(run_manifest_path) if run_manifest_path.exists() else None,
        "label_schema_path": str(label_schema_path) if label_schema_path.exists() else None,
        "export_summary_path": str(export_summary_path) if export_summary_path.exists() else None,
    }

    return RunSummary(
        run_id=run_id,
        state=state,
        out_root=str(out_dir),

        qc_summary_path=str(qc_summary_path) if qc_summary_path.exists() else None,
        run_log_path=str(run_log_path) if run_log_path.exists() else None,
        gt_jsonl_path=str(gt_jsonl_path) if gt_jsonl_path.exists() else None,

        train_split_path=str(train_split_path) if train_split_path.exists() else None,
        val_split_path=str(val_split_path) if val_split_path.exists() else None,
        test_split_path=str(test_split_path) if test_split_path.exists() else None,

        total=qc.get("total"),
        ok=qc.get("ok"),
        fail=qc.get("fail"),
        recovered=qc.get("recovered"),
        fallback_used=qc.get("fallback_used"),
        math_pages=qc.get("math_pages"),
        math_mask_nonempty_pages=qc.get("math_mask_nonempty_pages"),

        extra=extra,
    )