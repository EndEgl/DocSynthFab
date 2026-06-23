from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest


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

    def get_schema_for_ui(self):
        return []

    def start(self, req):
        self.started_req = req
        return "gui-run-1"

    def cancel(self, run_id):
        self.cancelled_run_id = run_id
        return True

    def get_status(self, run_id):
        return SimpleNamespace(
            run_id=run_id,
            state="done",
            pid=111,
            return_code=0,
            out_root="D:/gui_out",
            progress=SimpleNamespace(message="finished", to_dict=lambda: {"message": "finished"}),
            stdout_log="",
            stderr_log="",
            to_dict=lambda: {"run_id": run_id, "state": "done"},
        )

    def get_summary(self, run_id):
        return SimpleNamespace(to_dict=lambda: {"run_id": run_id, "state": "done"})


@pytest.mark.integration
def test_web_gui_state_start_run_builds_valid_run_request(monkeypatch):
    pytest.importorskip("nicegui")

    import docsynthfab.gui.web.app as web_mod
    from docsynthfab.gui.web.state import WebGuiState

    state = WebGuiState()
    state.orchestrator = DummyOrchestrator()

    state.config_path_input = DummyWidget("configs/default.yaml")
    state.out_root_input = DummyWidget("D:/gui_out")
    state.pages_input = DummyWidget(3)
    state.workers_input = DummyWidget(1)
    state.seed_input = DummyWidget(123)
    state.smoke_test_input = DummyWidget(False)

    state.start_btn = DummyWidget()
    state.stop_btn = DummyWidget()
    state.run_id_label = DummyWidget(text="-")
    state.state_label = DummyWidget(text="idle")
    state.out_root_label = DummyWidget(text="-")
    state.progress_label = DummyWidget(text="-")

    monkeypatch.setattr(web_mod, "_collect_all_overrides_for_run", lambda _state: {})
    monkeypatch.setattr(web_mod, "_refresh_status", lambda _state: None)
    monkeypatch.setattr(web_mod, "write_active_run_state", lambda **kwargs: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *a, **k: None)

    web_mod._start_run(state)

    req = state.orchestrator.started_req

    assert req is not None
    assert req.pages == 3
    assert req.workers == 1
    assert req.seed == 123
    assert state.current_run_id == "gui-run-1"


@pytest.mark.integration
def test_web_gui_refresh_and_stop_use_orchestrator(monkeypatch):
    pytest.importorskip("nicegui")

    import docsynthfab.gui.web.app as web_mod
    from docsynthfab.gui.web.state import WebGuiState

    state = WebGuiState()
    state.orchestrator = DummyOrchestrator()
    state.current_run_id = "gui-run-1"

    state.run_id_label = DummyWidget(text="-")
    state.state_label = DummyWidget(text="idle")
    state.pid_label = DummyWidget(text="-")
    state.return_code_label = DummyWidget(text="-")
    state.out_root_label = DummyWidget(text="-")
    state.progress_label = DummyWidget(text="-")
    state.status_json = DummyWidget()
    state.summary_json = DummyWidget()
    state.stdout_log = DummyWidget()
    state.stderr_log = DummyWidget()
    state.start_btn = DummyWidget()
    state.stop_btn = DummyWidget()

    monkeypatch.setattr(web_mod, "refresh_live_event_log", lambda _state: None)
    monkeypatch.setattr(web_mod, "clear_active_run_state", lambda: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *a, **k: None)

    web_mod._refresh_status(state)

    assert state.state_label.text == "done"
    assert state.pid_label.text == "111"

    web_mod._stop_run(state)

    assert state.orchestrator.cancelled_run_id == "gui-run-1"


