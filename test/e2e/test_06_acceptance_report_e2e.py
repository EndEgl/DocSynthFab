# test/e2e/test_06_acceptance_report_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9

from __future__ import annotations

from pathlib import Path

import pytest

from acceptance_report import append_metric_record, write_acceptance_report
from e2e_support import fresh_output_dir, run_backend_generation
from quality_metrics import measure_all_core_metrics


@pytest.mark.e2e
@pytest.mark.slow
def test_acceptance_quality_report_is_written(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "acceptance_report_source")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=3,
        workers=1,
        seed=999,
        overrides={
            "run.export_targets": ["native", "segformer", "coco"],
            "content.block_mix": {"text": 60, "table": 25, "latex": 15},
        },
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    metrics = measure_all_core_metrics(out_root)

    append_metric_record(
        project_root=project_root,
        test_name="test_acceptance_quality_report_is_written",
        metrics=metrics,
    )

    report = write_acceptance_report(
        project_root=project_root,
        suite_name="ai1_gen_e2e_acceptance",
        metrics=metrics,
    )

    json_report = project_root / "test_artifacts" / "acceptance_quality_report.json"
    md_report = project_root / "test_artifacts" / "acceptance_quality_report.md"

    assert json_report.exists()
    assert md_report.exists()
    assert report["decision"] in {"PASS", "FAIL", "UNKNOWN"}
    assert "overall_acceptance_score" in report["scores"]