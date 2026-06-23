from __future__ import annotations

from pathlib import Path

import pytest

from integration_support import assert_basic_output_tree, wait_for_run

@pytest.mark.integration
@pytest.mark.slow
def test_orchestrator_one_page_run_completes(run_orchestrator, make_run_request):
    req = make_run_request(out_name="one_page", pages=1, workers=1)
    run_id = run_orchestrator.start(req)

    status = wait_for_run(run_orchestrator, run_id)

    assert str(getattr(status, "state", "")) in {"done", "completed"}
    assert_basic_output_tree(Path(req.out_root), expected_pages=1)


@pytest.mark.integration
@pytest.mark.slow
def test_orchestrator_two_page_output_counts_match(run_orchestrator, make_run_request):
    req = make_run_request(out_name="two_pages", pages=2, workers=1)
    run_id = run_orchestrator.start(req)

    status = wait_for_run(run_orchestrator, run_id)

    assert str(getattr(status, "state", "")) in {"done", "completed"}
    assert_basic_output_tree(Path(req.out_root), expected_pages=2)


@pytest.mark.integration
@pytest.mark.slow
def test_orchestrator_status_and_summary_contract(run_orchestrator, make_run_request):
    req = make_run_request(out_name="status_summary", pages=1, workers=1)
    run_id = run_orchestrator.start(req)

    status = wait_for_run(run_orchestrator, run_id)
    summary = run_orchestrator.get_summary(run_id)

    assert getattr(status, "run_id", run_id) == run_id
    assert hasattr(status, "state")
    assert hasattr(summary, "to_dict")

    data = summary.to_dict()
    assert isinstance(data, dict)


@pytest.mark.integration
def test_orchestrator_cancel_unknown_or_terminal_run_is_safe(run_orchestrator):
    try:
        result = run_orchestrator.cancel("unknown-run-id")
    except Exception as exc:
        assert isinstance(exc, (KeyError, ValueError, RuntimeError))
    else:
        assert result in {False, True, None}



