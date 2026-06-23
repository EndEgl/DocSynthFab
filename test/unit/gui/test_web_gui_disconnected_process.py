from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import docsynthfab.gui.web.app as web_mod
import docsynthfab.gui.web.run_state as run_state_mod
from docsynthfab.gui.web.run_state import (
    current_run_is_active,
    restore_active_run_from_disk,
)
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

    state.state_label = DummyWidget(text="idle")
    state.run_id_label = DummyWidget(text="-")
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
    state.out_root_input = DummyWidget("D:/new_out")
    state.pages_input = DummyWidget(10)
    state.workers_input = DummyWidget(1)
    state.seed_input = DummyWidget(123)
    state.smoke_test_input = DummyWidget(False)

    return state


@dataclass
class FakeProgress:
    state: str = "running"
    message: str = "running"

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "message": self.message,
        }


@dataclass
class FakeStatus:
    run_id: str = "run"
    state: str = "running"
    pid: int | None = 1234
    return_code: int | None = None
    out_root: str = "D:/ai1_test"
    stdout_log: str | None = None
    stderr_log: str | None = None
    progress: FakeProgress | None = None

    def __post_init__(self) -> None:
        if self.progress is None:
            self.progress = FakeProgress("running", "running")

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "state": self.state,
            "pid": self.pid,
            "return_code": self.return_code,
            "out_root": self.out_root,
            "progress": self.progress.to_dict() if self.progress else {},
        }


@dataclass
class FakeSummary:
    out_root: str = "D:/ai1_test"
    qc_summary_path: str | None = None
    run_log_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "out_root": self.out_root,
            "qc_summary_path": self.qc_summary_path,
            "run_log_path": self.run_log_path,
        }


class OrchestratorProcessLost:
    def get_status(self, run_id: str) -> FakeStatus:
        raise KeyError("orch/unknown-run-id")

    def get_summary(self, run_id: str) -> FakeSummary:
        raise KeyError("orch/unknown-run-id")

    def cancel(self, run_id: str) -> bool:
        raise KeyError("orch/unknown-run-id")


class OrchestratorLostThenStartsClean:
    def __init__(self) -> None:
        self.started_req = None
        self.start_calls = 0

    def get_status(self, run_id: str) -> FakeStatus:
        if run_id == "old-lost-run":
            raise KeyError("orch/unknown-run-id")

        return FakeStatus(
            run_id=run_id,
            state="running",
            pid=999,
            return_code=None,
            out_root="D:/new_out",
            progress=FakeProgress("started", "started"),
        )

    def get_summary(self, run_id: str) -> FakeSummary:
        if run_id == "old-lost-run":
            raise KeyError("orch/unknown-run-id")

        return FakeSummary(out_root="D:/new_out")

    def start(self, req: Any) -> str:
        self.started_req = req
        self.start_calls += 1
        return "new-run-1"

    def cancel(self, run_id: str) -> bool:
        return True


def _write_active_state(path: Path, run_id: str = "old-lost-run") -> None:
    path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "state": "running",
                "out_root": "D:/ai1_test",
                "config_path": "configs/default.yaml",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_process_lost_during_status_refresh_stops_gui_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_state_path = tmp_path / "_active_run_state.json"
    _write_active_state(active_state_path, "old-lost-run")

    monkeypatch.setattr(run_state_mod, "ACTIVE_RUN_STATE_PATH", active_state_path)

    state = _make_state(OrchestratorProcessLost())
    state.current_run_id = "old-lost-run"

    events: list[tuple[str, str]] = []
    monkeypatch.setattr(
        web_mod,
        "append_gui_event",
        lambda _state, message, level="INFO": events.append((level, message)),
    )

    assert current_run_is_active(state) is False

    assert state.current_run_id is None
    assert state.last_unknown_run_id == "old-lost-run"
    assert not active_state_path.exists()

    assert state.state_label.text == "idle"
    assert state.run_id_label.text == "-"
    assert state.pid_label.text == "-"
    assert state.return_code_label.text == "-"
    assert state.out_root_label.text == "-"
    assert state.progress_label.text == "lost run state cleared"

    assert state.start_btn.disabled is False
    assert state.stop_btn.disabled is True

    assert state.last_unknown_run_id == "old-lost-run"
    assert state.progress_label.text == "lost run state cleared"



def test_process_lost_during_restore_does_not_keep_ghost_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_state_path = tmp_path / "_active_run_state.json"
    _write_active_state(active_state_path, "old-lost-run")

    monkeypatch.setattr(run_state_mod, "ACTIVE_RUN_STATE_PATH", active_state_path)

    state = _make_state(OrchestratorProcessLost())

    events: list[tuple[str, str]] = []
    monkeypatch.setattr(
        web_mod,
        "append_gui_event",
        lambda _state, message, level="INFO": events.append((level, message)),
    )

    restored = restore_active_run_from_disk(state)

    assert restored is None
    assert state.current_run_id is None
    assert state.last_unknown_run_id == "old-lost-run"
    assert not active_state_path.exists()

    assert state.state_label.text == "idle"
    assert state.progress_label.text == "lost run state cleared"



def test_process_lost_then_generate_starts_clean_new_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_state_path = tmp_path / "_active_run_state.json"
    _write_active_state(active_state_path, "old-lost-run")

    orch = OrchestratorLostThenStartsClean()
    state = _make_state(orch)

    monkeypatch.setattr(run_state_mod, "ACTIVE_RUN_STATE_PATH", active_state_path)
    monkeypatch.setattr(web_mod, "_collect_all_overrides_for_run", lambda _state: {})
    monkeypatch.setattr(web_mod, "_refresh_status", lambda _state: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *args, **kwargs: None)

    events: list[tuple[str, str]] = []
    monkeypatch.setattr(
        web_mod,
        "append_gui_event",
        lambda _state, message, level="INFO": events.append((level, message)),
    )

    web_mod._start_run(state)

    assert orch.start_calls == 1
    assert orch.started_req is not None

    assert state.current_run_id == "new-run-1"
    assert state.run_id_label.text == "new-run-1"
    assert state.state_label.text == "running"
    assert state.progress_label.text == "run started"
    assert state.out_root_label.text.replace("\\", "/") == "D:/new_out"

    assert state.start_btn.disabled is True
    assert state.stop_btn.disabled is False

    assert active_state_path.exists()
    state_obj = json.loads(active_state_path.read_text(encoding="utf-8"))
    assert state_obj["run_id"] == "new-run-1"
    assert state_obj["state"] == "running"
    assert state_obj["out_root"].replace("\\", "/") == "D:/new_out"



def test_process_lost_cancel_does_not_crash_gui(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_state_path = tmp_path / "_active_run_state.json"
    _write_active_state(active_state_path, "old-lost-run")

    monkeypatch.setattr(run_state_mod, "ACTIVE_RUN_STATE_PATH", active_state_path)

    state = _make_state(OrchestratorProcessLost())
    state.current_run_id = "old-lost-run"

    monkeypatch.setattr(web_mod, "safe_notify", lambda *args, **kwargs: None)

    web_mod._stop_run(state)

    assert state.current_run_id is None
    assert not active_state_path.exists()
    assert state.state_label.text == "idle"
    assert state.progress_label.text == "lost run state cleared"
    assert state.start_btn.disabled is False
    assert state.stop_btn.disabled is True



