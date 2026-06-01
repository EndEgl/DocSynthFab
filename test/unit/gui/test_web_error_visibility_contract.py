# test/unit/gui/test_web_error_visibility_contract.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import ai1_gen.gui.web.app as web_mod
from ai1_gen.gui.web.state import WebGuiState


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

    def set_content(self, value: Any) -> None:
        self.value = value
        self.text = str(value)


class ErrorStatusOrchestrator:
    def __init__(self, out_root: Path) -> None:
        self.out_root = out_root

    def get_status(self, run_id: str):
        return SimpleNamespace(
            run_id=run_id,
            state="failed",
            pid=123,
            return_code=1,
            out_root=str(self.out_root),
            progress=SimpleNamespace(message="failed during generation"),
            stdout_log=None,
            stderr_log=str(self.out_root / "stderr.log"),
            to_dict=lambda: {
                "run_id": run_id,
                "state": "failed",
                "return_code": 1,
                "out_root": str(self.out_root),
            },
        )

    def get_summary(self, run_id: str):
        return SimpleNamespace(
            to_dict=lambda: {
                "run_id": run_id,
                "state": "failed",
                "out_root": str(self.out_root),
            }
        )


def make_error_state(out_root: Path) -> WebGuiState:
    state = WebGuiState()
    state.current_run_id = "run-error-1"
    state.orchestrator = ErrorStatusOrchestrator(out_root)

    state.run_id_label = DummyWidget()
    state.state_label = DummyWidget()
    state.pid_label = DummyWidget()
    state.return_code_label = DummyWidget()
    state.out_root_label = DummyWidget()
    state.progress_label = DummyWidget()

    state.status_json = DummyWidget()
    state.summary_json = DummyWidget()
    state.stdout_log = DummyWidget()
    state.stderr_log = DummyWidget()
    state.live_event_log = DummyWidget()
    state.live_event_status_label = DummyWidget()

    state.start_btn = DummyWidget()
    state.stop_btn = DummyWidget()

    return state


def test_web_refresh_status_surfaces_failed_run_error_details(tmp_path, monkeypatch):
    out_root = tmp_path / "out"
    out_root.mkdir()

    (out_root / "stderr.log").write_text(
        "Traceback (most recent call last):\nValueError: synthetic failure\n",
        encoding="utf-8",
    )

    (out_root / "failed_pages.log").write_text(
        '{"event":"page_failed","page_id":"000003","stage":"render","error":"ValueError: synthetic failure"}\n',
        encoding="utf-8",
    )

    (out_root / "run.log").write_text(
        "page_failed page_id=000003 stage=render error=ValueError: synthetic failure\n",
        encoding="utf-8",
    )

    state = make_error_state(out_root)

    events: list[tuple[str, str]] = []

    monkeypatch.setattr(web_mod, "refresh_live_event_log", lambda _state: None)
    monkeypatch.setattr(web_mod, "clear_active_run_state", lambda: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        web_mod,
        "append_gui_event",
        lambda _state, message, level="INFO": events.append((level, str(message))),
    )

    web_mod._refresh_status(state)

    assert state.state_label.text == "failed"
    assert state.return_code_label.text == "1"
    assert state.start_btn.disabled is False
    assert state.stop_btn.disabled is True

    combined = (
        "\n".join(message for _level, message in events)
        + "\n"
        + str(state.stderr_log.value)
        + "\n"
        + str(state.stderr_log.text)
    )

    assert "synthetic failure" in combined
    assert "000003" in combined or "ValueError" in combined