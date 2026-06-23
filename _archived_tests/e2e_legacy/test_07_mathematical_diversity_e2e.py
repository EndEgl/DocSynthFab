# test/e2e/test_07_mathematical_diversity_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - numpy>=1.24,<3.0

from __future__ import annotations

from pathlib import Path

import pytest

from acceptance_report import append_metric_record
from e2e_support import fresh_output_dir, run_backend_generation
from quality_metrics import measure_mathematical_diversity


@pytest.mark.e2e
@pytest.mark.slow
def test_mathematical_diversity_50_pages_metrics(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    """
    Measure generated dataset diversity mathematically.

    This does not rely on external data. It checks whether the generator's own
    output distribution avoids layout collapse across 50 generated pages.
    """
    out_root = fresh_output_dir(e2e_out_root / "mathematical_diversity_50_pages")

    _orch, _run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=50,
        workers=1,
        seed=20260527,
        timeout_s=600.0,
        overrides={
            "run.export_targets": ["native"],
            "content.block_mix": {"text": 60, "table": 25, "latex": 15},
        },
    )

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    metrics = measure_mathematical_diversity(out_root)

    append_metric_record(
        project_root=project_root,
        test_name="test_mathematical_diversity_50_pages_metrics",
        metrics=metrics,
    )

    assert metrics["mathematical_diversity_pages"] == 50

    # İlk eşikler bilerek makul tutuldu. İlk gerçek sonuçtan sonra sıkılaştırırız.
    assert metrics["unique_layout_signature_ratio"] >= 0.30
    assert metrics["layout_entropy_normalized"] >= 0.30
    assert metrics["mathematical_diversity_score"] >= 0.45
    assert metrics["collapse_score"] <= 0.55



