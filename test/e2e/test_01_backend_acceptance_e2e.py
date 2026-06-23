from __future__ import annotations

from pathlib import Path

import pytest

from acceptance_report import append_metric_record, write_acceptance_report
from e2e_support import (
    assert_no_fatal_log_errors,
    assert_output_package_exists,
    assert_page_counts_match,
    fresh_output_dir,
    run_backend_generation,
    safe_e2e_overrides,
)
from quality_metrics import measure_all_core_metrics


@pytest.mark.e2e
@pytest.mark.slow
def test_backend_acceptance_package_e2e(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "backend_acceptance_package")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=3,
        workers=1,
        seed=123,
        timeout_s=240.0,
        overrides=safe_e2e_overrides("mixed_no_latex"),
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    assert_output_package_exists(out_root)
    assert_no_fatal_log_errors(out_root)

    counts = assert_page_counts_match(out_root, expected_pages=3)
    metrics = measure_all_core_metrics(out_root)

    metrics["interface"] = "backend"
    metrics.update(counts)

    append_metric_record(
        project_root=project_root,
        test_name="test_backend_acceptance_package_e2e",
        metrics=metrics,
    )

    write_acceptance_report(
        project_root=project_root,
        suite_name="backend_acceptance_package",
        metrics=metrics,
    )

    assert metrics["package_score"] == 1.0
    assert metrics["manifest_score"] == 1.0
    assert metrics["bbox_valid_ratio"] == 1.0
    assert metrics["ann_gt_text_match_ratio"] >= 0.80
    assert metrics["export_score"] >= 0.95