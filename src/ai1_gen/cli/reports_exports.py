# src/ai1_gen/cli/reports_exports.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from ai1_gen.exporters import export_dataset_package
from ai1_gen.reports import write_dataset_reports


def write_reports_safely(
    *,
    run_log: Path,
    out_root: Path,
    cfg_raw: Dict[str, Any],
    cfg_path: str,
    version: str,
    pages_requested: int,
    pages_ok: int,
    pages_fail: int,
    seed: int,
    workers: int,
    splits: Dict[str, int],
    qc_summary: Dict[str, Any],
    export_targets: list[str],
) -> None:
    try:
        report_result = write_dataset_reports(
            out_root=out_root,
            cfg_raw=cfg_raw,
            cfg_path=cfg_path,
            version=version,
            pages_requested=pages_requested,
            pages_ok=pages_ok,
            pages_fail=pages_fail,
            seed=seed,
            workers=workers,
            splits=splits,
            qc_summary=qc_summary,
            project_name="AI1 Gen",
            export_targets=export_targets,
        )

        with run_log.open("a", encoding="utf-8") as f:
            f.write(
                f"reports written reports_dir={report_result.get('reports_dir')} "
                f"feature_pages={report_result.get('page_count')}\n"
            )

    except Exception as e:
        with run_log.open("a", encoding="utf-8") as f:
            f.write(f"reports failed error={repr(e)}\n")


def write_exports_safely(
    *,
    run_log: Path,
    out_root: Path,
    export_targets: list[str],
) -> None:
    try:
        export_result = export_dataset_package(
            out_root=out_root,
            targets=export_targets,
        )

        with run_log.open("a", encoding="utf-8") as f:
            f.write(
                f"exports written targets={','.join(export_targets)} "
                f"summary={json.dumps(export_result, ensure_ascii=False)}\n"
            )

    except Exception as e:
        with run_log.open("a", encoding="utf-8") as f:
            f.write(f"exports failed error={repr(e)}\n")