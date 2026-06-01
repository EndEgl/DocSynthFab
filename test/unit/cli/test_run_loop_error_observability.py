# test/unit/cli/test_run_loop_error_observability.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9

from __future__ import annotations

import json

from ai1_gen.cli.run_loop import _record_failed_result, _record_future_exception


def test_record_failed_result_writes_failed_and_errors_logs(tmp_path):
    failed_log = tmp_path / "failed_pages.log"
    errors_log = tmp_path / "errors.jsonl"

    qc_summary = {"errors": {}}

    with failed_log.open("a", encoding="utf-8") as failed_f, errors_log.open("a", encoding="utf-8") as err_f:
        _record_failed_result(
            pid_hint="000003",
            result={
                "ok": False,
                "error": "synthetic failed result",
                "stage": "render",
            },
            qc_summary=qc_summary,
            failed_f=failed_f,
            err_f=err_f,
        )

    failed_text = failed_log.read_text(encoding="utf-8")
    err_lines = errors_log.read_text(encoding="utf-8").splitlines()

    assert "000003" in failed_text
    assert "synthetic failed result" in failed_text
    assert qc_summary["errors"]["runtime/fatal"] == 1

    rec = json.loads(err_lines[0])
    assert rec["page_id"] == "000003"
    assert rec["err_code"] == "runtime/fatal"
    assert "synthetic failed result" in str(rec["detail"])


def test_record_future_exception_writes_traceback_and_error_detail(tmp_path):
    failed_log = tmp_path / "failed_pages.log"
    errors_log = tmp_path / "errors.jsonl"

    qc_summary = {"errors": {}}

    try:
        raise RuntimeError("intentional observability failure")
    except RuntimeError as exc:
        with failed_log.open("a", encoding="utf-8") as failed_f, errors_log.open("a", encoding="utf-8") as err_f:
            _record_future_exception(
                pid_hint="000004",
                exc=exc,
                qc_summary=qc_summary,
                failed_f=failed_f,
                err_f=err_f,
            )

    failed_text = failed_log.read_text(encoding="utf-8")
    err_lines = errors_log.read_text(encoding="utf-8").splitlines()

    assert "000004" in failed_text
    assert "intentional observability failure" in failed_text
    assert qc_summary["errors"]["runtime/exception"] == 1

    rec = json.loads(err_lines[0])
    assert rec["page_id"] == "000004"
    assert rec["err_code"] == "runtime/exception"
    assert "intentional observability failure" in rec["detail"]
    assert "RuntimeError" in rec["traceback"]