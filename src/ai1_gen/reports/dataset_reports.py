# src/ai1_gen/reports/dataset_reports.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# This module uses only the Python standard library.
#
# Purpose:
# - Public orchestration entry point for dataset report generation.
# - The helper responsibilities live in smaller report modules.
# - This file preserves the external API: write_dataset_reports(...).

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .diversity_summary import (
    build_diversity_summary,
    write_diversity_summary_csv,
)
from .feature_extraction import (
    collect_feature_rows,
    extract_feature_row,
    write_features,
)
from .io_utils import _write_json, _write_text
from .label_schema import build_label_schema, label_schema_markdown
from .markdown_reports import build_dataset_card, diversity_report_markdown
from .run_manifest import write_run_manifest


LABEL_SCHEMA_VERSION = "document-ai-label-schema-v1"


__all__ = [
    "LABEL_SCHEMA_VERSION",
    "extract_feature_row",
    "collect_feature_rows",
    "write_features",
    "write_dataset_reports",
]


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
    Main function called at the end of the run.

    It writes report files without mutating the generated dataset outputs.

    Responsibilities:
    - label schema files
    - run manifest
    - dataset card
    - feature exports
    - diversity summary files

    It does not decide run identity/version details directly.
    The manifest writer owns manifest_version, run_id, created_at,
    version, and generator_version.
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
    _write_text(
        reports_dir / "diversity_report.md",
        diversity_report_markdown(summary),
    )

    return {
        "reports_dir": str(reports_dir),
        "manifest": manifest,
        "page_count": len(rows),
        "diversity_summary": summary,
    }