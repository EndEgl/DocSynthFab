# test/unit/gui/test_web_run_lifecycle_contract.py
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import docsynthfab.gui.web.app as web_mod
from docsynthfab.gui.web.state import WebGuiState


class DummyWidget:
    def __init__(self, value: Any = None, text: str = "") -> None:
        self.value = value
        self.text = text
        self.disabled = False

    def enable(self) -> None:
        self.disabled = False

    def disable(self) -> None:
        self.disabled = True

    def update(self) -> None:
        pass


class LifecycleOrchestrator:
    def __init__(self) -> None:
        self.cancelled_run_id = None
        self.cancel_result = True
        self.status_state = "cancelled"

    def cancel(self, run_id: str) -> bool:
        self.cancelled_run_id = run_id
        return self.cancel_result

    def get_status(self, run_id: str):
        return SimpleNamespace(
            run_id=run_id,
            state=self.status_state,
            pid=None,
            return_code=-15,
            out_root="D:/web_out",
            progress=SimpleNamespace(message=self.status_state),
            stdout_log=None,
            stderr_log=None,
            to_dict=lambda: {
                "run_id": run_id,
                "state": self.status_state,
                "return_code": -15,
            },
        )

    def get_summary(self, run_id: str):
        return SimpleNamespace(to_dict=lambda: {"run_id": run_id})


def make_lifecycle_state() -> WebGuiState:
    state = WebGuiState()
    state.orchestrator = LifecycleOrchestrator()
    state.current_run_id = "run-web-1"

    state.start_btn = DummyWidget()
    state.stop_btn = DummyWidget()
    state.start_btn.disable()
    state.stop_btn.enable()

    state.run_id_label = DummyWidget(text="run-web-1")
    state.state_label = DummyWidget(text="running")
    state.pid_label = DummyWidget(text="-")
    state.return_code_label = DummyWidget(text="-")
    state.out_root_label = DummyWidget(text="D:/web_out")
    state.progress_label = DummyWidget(text="running")

    state.status_json = DummyWidget()
    state.summary_json = DummyWidget()
    state.stdout_log = DummyWidget()
    state.stderr_log = DummyWidget()
    state.live_event_log = DummyWidget()
    state.live_event_status_label = DummyWidget()

    return state


def test_web_stop_success_reaches_cancelled_terminal_ui(monkeypatch):
    state = make_lifecycle_state()

    cleared = {"value": False}
    monkeypatch.setattr(web_mod, "clear_active_run_state", lambda: cleared.__setitem__("value", True))
    monkeypatch.setattr(web_mod, "refresh_live_event_log", lambda _state: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *args, **kwargs: None)

    web_mod._stop_run(state)

    assert state.orchestrator.cancelled_run_id == "run-web-1"

    # Stop should refresh into terminal cancelled state.
    assert state.state_label.text == "cancelled"
    assert state.progress_label.text == "cancelled"

    # Terminal UI must allow another run.
    assert state.start_btn.disabled is False
    assert state.stop_btn.disabled is True

    # Active-run disk marker must be cleared when terminal.
    assert cleared["value"] is True

def test_web_stop_cancel_failure_keeps_run_active(monkeypatch):
    state = make_lifecycle_state()
    state.orchestrator.cancel_result = False
    state.orchestrator.status_state = "running"

    cleared = {"value": False}
    monkeypatch.setattr(web_mod, "clear_active_run_state", lambda: cleared.__setitem__("value", True))
    monkeypatch.setattr(web_mod, "refresh_live_event_log", lambda _state: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *args, **kwargs: None)

    web_mod._stop_run(state)

    assert state.orchestrator.cancelled_run_id == "run-web-1"

    # Cancel failed, so it must still look active.
    assert state.state_label.text == "running"
    assert state.start_btn.disabled is True
    assert state.stop_btn.disabled is False

    # Disk active state should not be cleared while still running.
    assert cleared["value"] is False

def test_web_can_start_after_terminal_cancelled_state(monkeypatch):
    state = make_lifecycle_state()
    state.state_label.text = "cancelled"

    class StartCaptureOrchestrator(LifecycleOrchestrator):
        def __init__(self):
            super().__init__()
            self.started_req = None

        def start(self, req):
            self.started_req = req
            return "run-web-2"

    state.orchestrator = StartCaptureOrchestrator()

    state.config_path_input = DummyWidget("configs/default.yaml")
    state.out_root_input = DummyWidget("D:/web_out")
    state.pages_input = DummyWidget(1)
    state.workers_input = DummyWidget(1)
    state.seed_input = DummyWidget(123)
    state.smoke_test_input = DummyWidget(False)
    state.raw_yaml_override_input = DummyWidget("")

    monkeypatch.setattr(web_mod, "_collect_all_overrides_for_run", lambda _state: {})
    monkeypatch.setattr(web_mod, "write_active_run_state", lambda **kwargs: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(web_mod, "_refresh_status", lambda _state: None)

    web_mod._start_run(state)

    assert state.current_run_id == "run-web-2"
    assert state.orchestrator.started_req is not None
    assert state.start_btn.disabled is True
    assert state.stop_btn.disabled is False



