from __future__ import annotations

import os
from pathlib import Path

import pytest

from acceptance_report import append_metric_record
from e2e_support import fresh_output_dir, run_backend_generation, safe_e2e_overrides
from quality_metrics import measure_mathematical_diversity


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.diversity
def test_optional_mathematical_diversity_metrics(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    if os.getenv("DOCSYNTHFAB_RUN_DIVERSITY_E2E", "").strip() != "1":
        pytest.skip("Set DOCSYNTHFAB_RUN_DIVERSITY_E2E=1 to run diversity E2E.")

    out_root = fresh_output_dir(e2e_out_root / "mathematical_diversity")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=30,
        workers=1,
        seed=20260527,
        timeout_s=600.0,
        overrides=safe_e2e_overrides("mixed_no_latex"),
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    metrics = measure_mathematical_diversity(out_root)

    append_metric_record(
        project_root=project_root,
        test_name="test_optional_mathematical_diversity_metrics",
        metrics=metrics,
    )

    assert metrics["mathematical_diversity_pages"] == 30
    assert metrics["unique_layout_signature_ratio"] >= 0.25
    assert metrics["layout_entropy_normalized"] >= 0.25
    assert metrics["mathematical_diversity_score"] >= 0.35
    assert metrics["collapse_score"] <= 0.65