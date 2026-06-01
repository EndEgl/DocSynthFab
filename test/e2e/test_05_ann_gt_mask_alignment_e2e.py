# test/e2e/test_05_ann_gt_mask_alignment_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9

from __future__ import annotations

from pathlib import Path

import pytest

from acceptance_report import append_metric_record
from e2e_support import fresh_output_dir, run_backend_generation
from quality_metrics import (
    measure_ann_gt_alignment,
    measure_bbox_validity,
    measure_mask_bbox_alignment,
)


@pytest.mark.e2e
@pytest.mark.slow
def test_ann_gt_page_contract_metrics(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "ann_gt_page_contract")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=3,
        workers=1,
        seed=444,
        overrides={"content.block_mix": {"text": 70, "table": 20, "latex": 10}},
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    metrics = measure_ann_gt_alignment(out_root)

    append_metric_record(
        project_root=project_root,
        test_name="test_ann_gt_page_contract_metrics",
        metrics=metrics,
    )

    assert metrics["page_id_match_ratio"] == 1.0
    assert metrics["line_count_compatible_ratio"] >= 0.80


@pytest.mark.e2e
@pytest.mark.slow
def test_bbox_inside_page_metrics(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "bbox_inside_page")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=3,
        workers=1,
        seed=555,
        overrides={"content.block_mix": {"text": 60, "table": 25, "latex": 15}},
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    metrics = measure_bbox_validity(out_root)

    append_metric_record(
        project_root=project_root,
        test_name="test_bbox_inside_page_metrics",
        metrics=metrics,
    )

    assert metrics["bbox_valid_ratio"] == 1.0


@pytest.mark.e2e
@pytest.mark.slow
def test_gt_text_matches_ann_text_metrics(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "gt_text_matches_ann")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=3,
        workers=1,
        seed=666,
        overrides={"content.block_mix": {"text": 85, "table": 10, "latex": 5}},
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    metrics = measure_ann_gt_alignment(out_root)

    append_metric_record(
        project_root=project_root,
        test_name="test_gt_text_matches_ann_text_metrics",
        metrics=metrics,
    )

    assert metrics["page_id_match_ratio"] == 1.0
    assert metrics["page_text_similarity_mean"] >= 0.50


@pytest.mark.e2e
@pytest.mark.slow
def test_text_mask_bbox_alignment_metrics(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "text_mask_alignment")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=3,
        workers=1,
        seed=777,
        overrides={
            "content.block_mix": {"text": 100, "table": 0, "latex": 0},
            "render.latex.enable": False,
        },
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    metrics = measure_mask_bbox_alignment(out_root)

    append_metric_record(
        project_root=project_root,
        test_name="test_text_mask_bbox_alignment_metrics",
        metrics=metrics,
    )

    assert metrics["text_lines_checked"] > 0
    assert metrics["text_mask_bbox_hit_ratio"] >= 0.80


@pytest.mark.e2e
@pytest.mark.slow
def test_math_mask_bbox_alignment_metrics(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "math_mask_alignment")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=3,
        workers=1,
        seed=888,
        overrides={
            "content.block_mix": {"text": 0, "table": 0, "latex": 100},
            "render.latex.enable": True,
        },
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    metrics = measure_mask_bbox_alignment(out_root)

    append_metric_record(
        project_root=project_root,
        test_name="test_math_mask_bbox_alignment_metrics",
        metrics=metrics,
    )

    assert metrics["math_lines_checked"] >= 0
    assert metrics["math_mask_bbox_hit_ratio"] >= 0.50