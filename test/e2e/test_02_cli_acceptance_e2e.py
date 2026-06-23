from __future__ import annotations

from pathlib import Path

import pytest

from acceptance_report import append_metric_record
from e2e_support import (
    assert_no_fatal_log_errors,
    assert_output_package_exists,
    assert_page_counts_match,
    fresh_output_dir,
    run_cli_generation,
    write_safe_e2e_config,
)
from quality_metrics import measure_all_core_metrics


@pytest.mark.e2e
@pytest.mark.slow
def test_cli_acceptance_package_e2e(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "cli_acceptance_package")

    safe_config = write_safe_e2e_config(
        project_root=project_root,
        base_config_path=e2e_default_config,
        out_root=out_root,
        pages=2,
        workers=1,
        seed=321,
        profile="text",
    )

    result = run_cli_generation(
        project_root=project_root,
        config_path=safe_config,
        out_root=out_root,
        pages=2,
        workers=1,
        seed=321,
        export="native",
        timeout_s=240.0,
    )

    assert result.returncode == 0, {
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }

    assert_output_package_exists(out_root)
    assert_no_fatal_log_errors(out_root)
    counts = assert_page_counts_match(out_root, expected_pages=2)

    metrics = measure_all_core_metrics(out_root)
    metrics["interface"] = "cli"
    metrics.update(counts)

    append_metric_record(
        project_root=project_root,
        test_name="test_cli_acceptance_package_e2e",
        metrics=metrics,
    )

    assert metrics["package_score"] == 1.0
    assert metrics["manifest_score"] == 1.0
    assert metrics["bbox_valid_ratio"] == 1.0
    assert metrics["export_score"] >= 0.95