from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import ai1_gen.gui.web.app as web_mod
from ai1_gen.gui.web.state import WebGuiState


class DummyWidget:
    def __init__(self, value: Any = None, text: str = ""):
        self.value = value
        self.text = text
        self.disabled = False

    def enable(self):
        self.disabled = False

    def disable(self):
        self.disabled = True

    def update(self):
        pass

    def set_content(self, value):
        self.value = value
        self.text = str(value)


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
            run_id=run_id,
            state="done",
            pid=222,
            return_code=0,
            out_root="D:/web_out",
            progress=SimpleNamespace(state="finished", message="finished", to_dict=lambda: {"state": "finished"}),
            stdout_log="",
            stderr_log="",
            to_dict=lambda: {"run_id": run_id, "state": "done"},
        )

    def get_summary(self, run_id):
        return SimpleNamespace(
            to_dict=lambda: {"run_id": run_id, "state": "done"},
            out_root="D:/web_out",
            qc_summary_path="D:/web_out/qc_summary.json",
            run_log_path="D:/web_out/run.log",
        )


def make_state():
    state = WebGuiState()
    state.orchestrator = DummyOrchestrator()

    state.config_path_input = DummyWidget("configs/default.yaml")
    state.out_root_input = DummyWidget("D:/web_out")
    state.pages_input = DummyWidget(10)
    state.workers_input = DummyWidget(2)
    state.seed_input = DummyWidget(123)
    state.smoke_test_input = DummyWidget(False)

    state.start_btn = DummyWidget()
    state.stop_btn = DummyWidget()
    state.stop_btn.disable()

    state.run_id_label = DummyWidget(text="-")
    state.state_label = DummyWidget(text="idle")
    state.pid_label = DummyWidget(text="-")
    state.return_code_label = DummyWidget(text="-")
    state.out_root_label = DummyWidget(text="-")
    state.progress_label = DummyWidget(text="no active run")

    state.status_json = DummyWidget()
    state.summary_json = DummyWidget()
    state.stdout_log = DummyWidget()
    state.stderr_log = DummyWidget()

    return state


def test_web_collect_overrides_empty(monkeypatch):
    state = make_state()
    monkeypatch.setattr(web_mod, "_collect_simple_overrides", lambda _state: {})
    monkeypatch.setattr(web_mod, "collect_overrides", lambda *a, **k: {})

    assert web_mod._collect_all_overrides_for_run(state) == {}


def test_web_start_run_sets_state(monkeypatch):
    state = make_state()

    monkeypatch.setattr(web_mod, "_collect_all_overrides_for_run", lambda _state: {})
    monkeypatch.setattr(web_mod, "_refresh_status", lambda _state: None)
    monkeypatch.setattr(web_mod, "write_active_run_state", lambda **kwargs: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *args, **kwargs: None)

    web_mod._start_run(state)

    assert state.current_run_id == "run-web-1"
    assert state.run_id_label.text == "run-web-1"
    assert state.state_label.text == "running"


def test_web_stop_run_calls_cancel(monkeypatch):
    state = make_state()
    state.current_run_id = "run-web-1"

    monkeypatch.setattr(web_mod, "clear_active_run_state", lambda: None)
    monkeypatch.setattr(web_mod, "_refresh_status", lambda _state: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *args, **kwargs: None)

    web_mod._stop_run(state)

    assert state.orchestrator.cancelled_run_id == "run-web-1"


def test_web_refresh_status_updates_panels(monkeypatch):
    state = make_state()
    state.current_run_id = "run-web-1"

    monkeypatch.setattr(web_mod, "refresh_live_event_log", lambda _state: None)
    monkeypatch.setattr(web_mod, "clear_active_run_state", lambda: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *args, **kwargs: None)

    web_mod._refresh_status(state)

    assert state.state_label.text == "done"
    assert state.pid_label.text == "222"
    assert state.return_code_label.text == "0"
    assert state.out_root_label.text.replace("\\", "/") == "D:/web_out"
    assert state.progress_label.text == "finished"