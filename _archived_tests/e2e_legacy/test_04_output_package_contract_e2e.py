# test/e2e/test_04_output_package_contract_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9

from __future__ import annotations

from pathlib import Path

import pytest

from acceptance_report import append_metric_record
from e2e_support import (
    assert_output_package_exists,
    assert_page_counts_match,
    fresh_output_dir,
    run_backend_generation,
)
from quality_metrics import measure_manifest_contract, measure_output_package


@pytest.mark.e2e
@pytest.mark.slow
def test_output_package_required_dirs_and_files(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "output_package_required")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=3,
        workers=1,
        seed=111,
        overrides={
            "run.export_targets": ["native", "segformer", "coco"],
            "content.block_mix": {"text": 60, "table": 25, "latex": 15},
        },
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    assert_output_package_exists(out_root)

    metrics = measure_output_package(out_root)

    append_metric_record(
        project_root=project_root,
        test_name="test_output_package_required_dirs_and_files",
        metrics=metrics,
    )

    assert metrics["required_dirs_found_ratio"] == 1.0
    assert metrics["required_files_found_ratio"] == 1.0
    assert metrics["package_score"] == 1.0


@pytest.mark.e2e
@pytest.mark.slow
def test_output_counts_match_pages_ok(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "output_counts_match")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=4,
        workers=1,
        seed=222,
        overrides={
            "content.block_mix": {"text": 80, "table": 20, "latex": 0},
            "render.latex.enable": False,
        },
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    counts = assert_page_counts_match(out_root, expected_pages=4)
    manifest_metrics = measure_manifest_contract(out_root)

    metrics = {
        **counts,
        **manifest_metrics,
        "count_consistency_score": 1.0,
    }

    append_metric_record(
        project_root=project_root,
        test_name="test_output_counts_match_pages_ok",
        metrics=metrics,
    )

    assert counts["image_count"] == manifest_metrics["pages_ok"]
    assert counts["ann_count"] == manifest_metrics["pages_ok"]
    assert counts["gt_count"] == manifest_metrics["pages_ok"]


@pytest.mark.e2e
@pytest.mark.slow
def test_manifest_contract_metrics(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "manifest_contract")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=2,
        workers=1,
        seed=333,
        overrides={"run.export_targets": ["native", "coco"]},
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    metrics = measure_manifest_contract(out_root)

    append_metric_record(
        project_root=project_root,
        test_name="test_manifest_contract_metrics",
        metrics=metrics,
    )

    assert metrics["manifest_score"] == 1.0
    assert metrics["has_run_id"] is True
    assert metrics["has_created_at"] is True
    assert metrics["has_generator_version"] is True



