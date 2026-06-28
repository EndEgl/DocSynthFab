from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import docsynthfab.gui.web.app as web_mod
import docsynthfab.gui.web.run_state as run_state_mod
from docsynthfab.gui.web.run_state import current_run_is_active
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

    def set_text(self, text: str) -> None:
        self.text = str(text)

    def set_content(self, value: Any) -> None:
        self.value = value
        self.text = str(value)


def _make_state(orch=None) -> WebGuiState:
    state = WebGuiState()
    state.orchestrator = orch

    state.run_id_label = DummyWidget(text="-")
    state.state_label = DummyWidget(text="idle")
    state.pid_label = DummyWidget(text="-")
    state.return_code_label = DummyWidget(text="-")
    state.out_root_label = DummyWidget(text="-")
    state.progress_label = DummyWidget(text="no active run")
    state.start_btn = DummyWidget()
    state.stop_btn = DummyWidget()
    state.stop_btn.disable()

    state.status_json = DummyWidget()
    state.summary_json = DummyWidget()
    state.stdout_log = DummyWidget()
    state.stderr_log = DummyWidget()

    state.config_path_input = DummyWidget("configs/default.yaml")
    state.out_root_input = DummyWidget("D:/ai1_test")
    state.pages_input = DummyWidget(10)
    state.workers_input = DummyWidget(1)
    state.seed_input = DummyWidget(123)
    state.smoke_test_input = DummyWidget(False)

    return state


class OrchestratorAlwaysUnknown:
    def __init__(self) -> None:
        self.get_status_calls = 0
        self.get_summary_calls = 0

    def get_status(self, run_id: str):
        self.get_status_calls += 1
        raise KeyError("orch/unknown-run-id")

    def get_summary(self, run_id: str):
        self.get_summary_calls += 1
        raise KeyError("orch/unknown-run-id")


class FakeProgress:
    def __init__(self, state: str = "rendering", message: str = "rendering") -> None:
        self.state = state
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "message": self.message,
        }


class FakeStatus:
    def __init__(self, run_id: str = "run-ok") -> None:
        self.run_id = run_id
        self.state = "running"
        self.pid = 1234
        self.return_code = None
        self.out_root = "D:/ai1_test"
        self.stdout_log = None
        self.stderr_log = None
        self.progress = FakeProgress("rendering", "rendering")

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "state": self.state,
            "pid": self.pid,
            "return_code": self.return_code,
            "out_root": self.out_root,
            "progress": self.progress.to_dict(),
        }


class FakeSummary:
    def to_dict(self) -> dict[str, Any]:
        return {"ok": True}


class OrchestratorStableRunning:
    def __init__(self) -> None:
        self.get_status_calls = 0
        self.get_summary_calls = 0

    def get_status(self, run_id: str) -> FakeStatus:
        self.get_status_calls += 1
        return FakeStatus(run_id=run_id)

    def get_summary(self, run_id: str) -> FakeSummary:
        self.get_summary_calls += 1
        return FakeSummary()


def test_unknown_run_is_not_polled_again_after_first_clear(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_state_path = tmp_path / "_active_run_state.json"
    active_state_path.write_text(
        json.dumps({"run_id": "ghost-run", "state": "running"}),
        encoding="utf-8",
    )

    orch = OrchestratorAlwaysUnknown()
    monkeypatch.setattr(run_state_mod, "ACTIVE_RUN_STATE_PATH", active_state_path)

    state = _make_state(orch)
    state.current_run_id = "ghost-run"

    events: list[tuple[str, str]] = []
    monkeypatch.setattr(
        web_mod,
        "append_gui_event",
        lambda _state, message, level="INFO": events.append((level, message)),
    )

    assert current_run_is_active(state) is False

    assert orch.get_status_calls == 1
    assert state.current_run_id is None
    assert state.last_unknown_run_id == "ghost-run"
    assert not active_state_path.exists()
    assert state.state_label.text == "idle"
    assert state.progress_label.text == "lost run state cleared"

    for _ in range(10):
        web_mod._refresh_status(state)

    assert orch.get_status_calls == 1
    assert state.state_label.text == "idle"


def test_status_refresh_can_run_repeatedly_without_losing_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orch = OrchestratorStableRunning()
    state = _make_state(orch)
    state.current_run_id = "run-ok"

    monkeypatch.setattr(web_mod, "refresh_live_event_log", lambda _state: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *args, **kwargs: None)

    for _ in range(10):
        web_mod._refresh_status(state)

    assert orch.get_status_calls == 10
    assert orch.get_summary_calls == 10
    assert state.current_run_id == "run-ok"
    assert state.run_id_label.text == "run-ok"
    assert state.state_label.text == "running"
    assert state.pid_label.text == "1234"
    assert state.return_code_label.text == "-"
    assert state.out_root_label.text.replace("\\", "/") == "D:/ai1_test"
    assert state.progress_label.text == "rendering"
    assert state.start_btn.disabled is True
    assert state.stop_btn.disabled is False


def test_web_app_uses_state_driven_refresh_contract() -> None:
    assert hasattr(web_mod, "_refresh_status")
    assert hasattr(web_mod, "_start_run")
    assert hasattr(web_mod, "_stop_run")


def test_refresh_status_without_active_run_keeps_idle_state() -> None:
    state = _make_state(OrchestratorStableRunning())
    state.current_run_id = None

    web_mod._refresh_status(state)

    assert state.current_run_id is None
    assert state.run_id_label.text == "-"
    assert state.state_label.text == "idle"
    assert state.pid_label.text == "-"
    assert state.return_code_label.text == "-"
    assert state.progress_label.text == "no active run"
    assert state.start_btn.disabled is False
    assert state.stop_btn.disabled is True


def test_unknown_run_cleanup_does_not_raise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_state_path = tmp_path / "_active_run_state.json"
    active_state_path.write_text(
        json.dumps({"run_id": "ghost-run", "state": "running"}),
        encoding="utf-8",
    )

    orch = OrchestratorAlwaysUnknown()
    monkeypatch.setattr(run_state_mod, "ACTIVE_RUN_STATE_PATH", active_state_path)

    state = _make_state(orch)
    state.current_run_id = "ghost-run"

    assert current_run_is_active(state) is False

    assert state.current_run_id is None
    assert state.last_unknown_run_id == "ghost-run"
    assert not active_state_path.exists()
    assert state.state_label.text == "idle"
    assert state.progress_label.text == "lost run state cleared"



