from __future__ import annotations

import json
from pathlib import Path

import pytest

from integration_support import wait_for_run


@pytest.mark.integration
@pytest.mark.slow
def test_reports_manifest_is_written(run_orchestrator, make_run_request):
    req = make_run_request(out_name="reports_manifest", pages=1, workers=1)
    run_id = run_orchestrator.start(req)
    status = wait_for_run(run_orchestrator, run_id)

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    reports_dir = Path(req.out_root) / "reports"
    manifest = reports_dir / "run_manifest.json"

    assert manifest.exists()

    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert "project_name" in data
    assert "version" in data
    assert "pages_requested" in data


@pytest.mark.integration
@pytest.mark.slow
def test_dataset_report_files_are_written(run_orchestrator, make_run_request):
    req = make_run_request(out_name="dataset_reports", pages=1, workers=1)
    run_id = run_orchestrator.start(req)
    status = wait_for_run(run_orchestrator, run_id)

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    reports_dir = Path(req.out_root) / "reports"

    assert (reports_dir / "dataset_card.md").exists()
    assert (reports_dir / "diversity_summary.json").exists()
    assert (reports_dir / "diversity_report.md").exists()


@pytest.mark.integration
@pytest.mark.slow
def test_exports_directory_exists_after_run(run_orchestrator, make_run_request):
    req = make_run_request(out_name="exports_dir", pages=1, workers=1)
    run_id = run_orchestrator.start(req)
    status = wait_for_run(run_orchestrator, run_id)

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    exports_dir = Path(req.out_root) / "exports"
    assert exports_dir.exists()