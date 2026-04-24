from __future__ import annotations

from types import SimpleNamespace

import ai1_gen.web_gui as web_mod


class DummyWidget:
    def __init__(self, value=None):
        self.value = value
        self.text = ""
        self.disabled = False

    def enable(self):
        self.disabled = False

    def disable(self):
        self.disabled = True


class DummyOrchestrator:
    def __init__(self):
        self.started_req = None
        self.cancelled_run_id = None

    def start(self, req):
        self.started_req = req
        return "run-web-1"

    def cancel(self, run_id):
        self.cancelled_run_id = run_id
        return True

    def get_status(self, run_id):
        return SimpleNamespace(
            state="done",
            pid=222,
            return_code=0,
            out_root="D:/web_out",
            progress=SimpleNamespace(state="finished"),
            stdout_log="stdout text",
            stderr_log="stderr text",
        )

    def get_summary(self, run_id):
        return SimpleNamespace(
            to_dict=lambda: {"run_id": run_id, "state": "done"},
            out_root="D:/web_out",
            qc_summary_path="D:/web_out/qc_summary.json",
            run_log_path="D:/web_out/run.log",
        )


def setup_dummy_globals(monkeypatch):
    monkeypatch.setattr(web_mod, "orchestrator", DummyOrchestrator())
    monkeypatch.setattr(web_mod, "field_widgets", {})
    monkeypatch.setattr(web_mod, "current_run_id", None)

    web_mod.config_path_input = DummyWidget("configs/default.yaml")
    web_mod.out_root_input = DummyWidget("D:/web_out")
    web_mod.pages_input = DummyWidget(10)
    web_mod.workers_input = DummyWidget(2)
    web_mod.seed_input = DummyWidget(123)
    web_mod.smoke_test_input = DummyWidget(False)

    web_mod.run_id_label = DummyWidget()
    web_mod.state_label = DummyWidget()
    web_mod.pid_label = DummyWidget()
    web_mod.return_code_label = DummyWidget()
    web_mod.out_root_label = DummyWidget()
    web_mod.progress_label = DummyWidget()

    web_mod.status_json = DummyWidget("")
    web_mod.summary_json = DummyWidget("")
    web_mod.stdout_log = DummyWidget("")
    web_mod.stderr_log = DummyWidget("")

    web_mod.start_btn = DummyWidget()
    web_mod.stop_btn = DummyWidget()


def test_web_collect_overrides_empty(monkeypatch):
    setup_dummy_globals(monkeypatch)
    assert web_mod._collect_overrides() == {}


def test_web_start_run_sets_state(monkeypatch):
    setup_dummy_globals(monkeypatch)
    monkeypatch.setattr(web_mod.ui, "notify", lambda *a, **k: None)

    web_mod._start_run()

    assert web_mod.current_run_id == "run-web-1"
    assert web_mod.run_id_label.text == "run-web-1"
    assert web_mod.state_label.text == "running"
    assert web_mod.progress_label.text == "started"


def test_web_stop_run_calls_cancel(monkeypatch):
    setup_dummy_globals(monkeypatch)
    monkeypatch.setattr(web_mod.ui, "notify", lambda *a, **k: None)
    web_mod.current_run_id = "run-web-1"

    web_mod._stop_run()

    assert web_mod.orchestrator.cancelled_run_id == "run-web-1"
    assert web_mod.state_label.text == "cancelled"


def test_web_refresh_status_updates_panels(monkeypatch):
    setup_dummy_globals(monkeypatch)
    monkeypatch.setattr(web_mod.ui, "notify", lambda *a, **k: None)
    web_mod.current_run_id = "run-web-1"

    web_mod._refresh_status_panels()

    assert web_mod.state_label.text == "done"
    assert web_mod.pid_label.text == "222"
    assert web_mod.return_code_label.text == "0"
    assert web_mod.out_root_label.text == "D:/web_out"
    assert web_mod.progress_label.text == "finished"
    