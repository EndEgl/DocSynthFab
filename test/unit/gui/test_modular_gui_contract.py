# test/unit/gui/test_modular_gui_contract.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - nicegui>=2.0,<3.0
# - PySide6>=6.5,<7.0
# - pytest-qt>=4.4,<5.0

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any

import pytest


# ======================================================================================
# Shared GUI package contracts
# ======================================================================================

def test_gui_root_package_is_side_effect_free():
    import ai1_gen.gui as gui

    assert hasattr(gui, "__all__")
    assert gui.__all__ == []


def test_web_gui_package_is_side_effect_free():
    import ai1_gen.gui.web as web

    assert hasattr(web, "__all__")
    assert web.__all__ == []


def test_desktop_gui_package_is_side_effect_free():
    import ai1_gen.gui.desktop as desktop

    assert hasattr(desktop, "__all__")
    assert desktop.__all__ == []


def test_shared_paths_contract():
    from ai1_gen.gui.shared.paths import (
        DEFAULT_CONFIG,
        PACKAGE_ROOT,
        PROJECT_ROOT,
        SRC_ROOT,
        normalize_config_path,
        normalize_out_root,
        open_path,
    )

    assert PROJECT_ROOT.exists()
    assert SRC_ROOT.exists()
    assert PACKAGE_ROOT.exists()
    assert DEFAULT_CONFIG is not None

    assert callable(normalize_config_path)
    assert callable(normalize_out_root)
    assert callable(open_path)


# ======================================================================================
# Web GUI unit contracts
# ======================================================================================

class DummyWebWidget:
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
        self.text = text


class DummyJsonWidget(DummyWebWidget):
    def set_content(self, value: Any) -> None:
        self.value = value
        self.text = str(value)


class DummyLogWidget(DummyWebWidget):
    def set_content(self, value: Any) -> None:
        self.value = value
        self.text = str(value)


class DummyWebProgress:
    def __init__(self, state: str = "finished", message: str = "finished") -> None:
        self.state = state
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "message": self.message,
        }


class DummyWebStatus:
    def __init__(self, run_id: str = "web-run-123", state: str = "done") -> None:
        self.run_id = run_id
        self.state = state
        self.pid = 111
        self.return_code = 0
        self.out_root = "D:/web_out"
        self.stdout_log = ""
        self.stderr_log = ""
        self.progress = DummyWebProgress()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "state": self.state,
            "pid": self.pid,
            "return_code": self.return_code,
            "out_root": self.out_root,
            "progress": self.progress.to_dict(),
        }


class DummyWebSummary:
    def __init__(self, run_id: str = "web-run-123") -> None:
        self.run_id = run_id
        self.out_root = "D:/web_out"
        self.qc_summary_path = "D:/web_out/qc_summary.json"
        self.run_log_path = "D:/web_out/run.log"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "out_root": self.out_root,
            "qc_summary_path": self.qc_summary_path,
            "run_log_path": self.run_log_path,
        }


class DummyWebOrchestrator:
    def __init__(self) -> None:
        self.started_req = None
        self.cancelled_run_id = None

    def get_schema_for_ui(self):
        return []

    def start(self, req):
        self.started_req = req
        return "web-run-123"

    def cancel(self, run_id):
        self.cancelled_run_id = run_id
        return True

    def get_status(self, run_id):
        return DummyWebStatus(run_id=run_id, state="done")

    def get_summary(self, run_id):
        return DummyWebSummary(run_id=run_id)


def _make_web_state():
    from ai1_gen.gui.web.state import WebGuiState

    state = WebGuiState()
    state.orchestrator = DummyWebOrchestrator()

    state.config_path_input = DummyWebWidget("configs/default.yaml")
    state.out_root_input = DummyWebWidget("D:/web_out")
    state.pages_input = DummyWebWidget(10)
    state.workers_input = DummyWebWidget(2)
    state.seed_input = DummyWebWidget(123)
    state.smoke_test_input = DummyWebWidget(False)

    state.start_btn = DummyWebWidget()
    state.stop_btn = DummyWebWidget()
    state.stop_btn.disable()

    state.run_id_label = DummyWebWidget(text="-")
    state.state_label = DummyWebWidget(text="idle")
    state.pid_label = DummyWebWidget(text="-")
    state.return_code_label = DummyWebWidget(text="-")
    state.out_root_label = DummyWebWidget(text="-")
    state.progress_label = DummyWebWidget(text="no active run")

    state.status_json = DummyJsonWidget("")
    state.summary_json = DummyJsonWidget("")
    state.stdout_log = DummyLogWidget("")
    state.stderr_log = DummyLogWidget("")

    return state


def test_web_runtime_state_owner_exists():
    from ai1_gen.gui.web.state import WEB_STATE, WebGuiState

    assert isinstance(WEB_STATE, WebGuiState)
    assert hasattr(WEB_STATE, "orchestrator")
    assert hasattr(WEB_STATE, "current_run_id")
    assert hasattr(WEB_STATE, "run_lock")


def test_web_gui_app_imports_when_nicegui_is_available():
    pytest.importorskip("nicegui")

    mod = importlib.import_module("ai1_gen.gui.web.app")

    assert hasattr(mod, "STATE")
    assert hasattr(mod, "_start_run")
    assert hasattr(mod, "_stop_run")
    assert hasattr(mod, "_refresh_status")
    assert hasattr(mod, "_collect_all_overrides_for_run")


def test_web_start_run_updates_state(monkeypatch):
    pytest.importorskip("nicegui")

    import ai1_gen.gui.web.app as web_app

    state = _make_web_state()

    monkeypatch.setattr(web_app, "_collect_all_overrides_for_run", lambda _state: {})
    monkeypatch.setattr(web_app, "_refresh_status", lambda _state: None)
    monkeypatch.setattr(web_app, "write_active_run_state", lambda **kwargs: None)
    monkeypatch.setattr(web_app, "safe_notify", lambda *args, **kwargs: None)

    web_app._start_run(state)

    assert state.current_run_id == "web-run-123"
    assert state.run_id_label.text == "web-run-123"
    assert state.state_label.text == "running"
    assert state.out_root_label.text.replace("\\", "/") == "D:/web_out"
    assert state.progress_label.text == "run started"
    assert state.start_btn.disabled is True
    assert state.stop_btn.disabled is False
    assert state.orchestrator.started_req is not None


def test_web_stop_run_calls_orchestrator(monkeypatch):
    pytest.importorskip("nicegui")

    import ai1_gen.gui.web.app as web_app

    state = _make_web_state()
    state.current_run_id = "web-run-123"

    monkeypatch.setattr(web_app, "clear_active_run_state", lambda: None)
    monkeypatch.setattr(web_app, "_refresh_status", lambda _state: None)
    monkeypatch.setattr(web_app, "safe_notify", lambda *args, **kwargs: None)

    web_app._stop_run(state)

    assert state.orchestrator.cancelled_run_id == "web-run-123"


def test_web_refresh_status_reads_orchestrator(monkeypatch):
    pytest.importorskip("nicegui")

    import ai1_gen.gui.web.app as web_app

    state = _make_web_state()
    state.current_run_id = "web-run-123"

    monkeypatch.setattr(web_app, "refresh_live_event_log", lambda _state: None)
    monkeypatch.setattr(web_app, "clear_active_run_state", lambda: None)
    monkeypatch.setattr(web_app, "safe_notify", lambda *args, **kwargs: None)

    web_app._refresh_status(state)

    assert state.run_id_label.text == "web-run-123"
    assert state.state_label.text == "done"
    assert state.pid_label.text == "111"
    assert state.return_code_label.text == "0"
    assert state.out_root_label.text.replace("\\", "/") == "D:/web_out"
    assert state.progress_label.text == "finished"
    assert state.start_btn.disabled is False
    assert state.stop_btn.disabled is True


# ======================================================================================
# Desktop GUI unit contracts
# ======================================================================================

class DummyDesktopProgress:
    def __init__(self, state: str = "finished", message: str = "finished") -> None:
        self.state = state
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "message": self.message,
        }


class DummyDesktopStatus:
    def __init__(self, run_id: str = "desktop-run-123", state: str = "done") -> None:
        self.run_id = run_id
        self.state = state
        self.pid = 222
        self.return_code = 0
        self.out_root = "D:/desktop_out"
        self.stdout_log = ""
        self.stderr_log = ""
        self.progress = DummyDesktopProgress()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "state": self.state,
            "pid": self.pid,
            "return_code": self.return_code,
            "out_root": self.out_root,
            "progress": self.progress.to_dict(),
        }


class DummyDesktopSummary:
    def __init__(self, run_id: str = "desktop-run-123") -> None:
        self.run_id = run_id
        self.out_root = "D:/desktop_out"
        self.qc_summary_path = "D:/desktop_out/qc_summary.json"
        self.run_log_path = "D:/desktop_out/run.log"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "out_root": self.out_root,
            "qc_summary_path": self.qc_summary_path,
            "run_log_path": self.run_log_path,
        }


class DummyDesktopOrchestrator:
    def __init__(self) -> None:
        self.started_req = None
        self.cancelled_run_id = None

    def get_schema_for_ui(self, mode=None):
        return []

    def build_effective_config_yaml_text(self, **kwargs):
        return "version: ai1-ds-v1.3.2\n"

    def build_baseline_override_map(self, config_path: str, *, visibility: str = "advanced"):
        return {}

    def build_config_with_user_override(
        self,
        *,
        config_path: str,
        overrides=None,
        raw_yaml_override_text=None,
    ):
        return {
            "version": "ai1-ds-v1.3.2",
            "io": {"out_root": "D:/desktop_out"},
            "run": {
                "pages": 10,
                "workers": 2,
                "seed": 123,
                "splits": {"train": 0.8, "val": 0.1, "test": 0.1},
            },
            "qc": {},
            "thresholds": {},
            "augment": {"enable": False},
            "telemetry": {},
        }

    def get_user_config_path(self, config_path: str):
        return "D:/desktop_out/user_config.yaml"

    def start(self, req):
        self.started_req = req
        return "desktop-run-123"

    def cancel(self, run_id):
        self.cancelled_run_id = run_id
        return True

    def get_status(self, run_id):
        return DummyDesktopStatus(run_id=run_id, state="done")

    def get_summary(self, run_id):
        return DummyDesktopSummary(run_id=run_id)


def test_desktop_gui_app_imports_when_pyside6_is_available():
    pytest.importorskip("PySide6")

    mod = importlib.import_module("ai1_gen.gui.desktop.app")

    assert hasattr(mod, "DesktopMainWindow")
    assert hasattr(mod, "DesktopRunInput")
    assert hasattr(mod, "main")


def test_desktop_window_constructs(qtbot, monkeypatch):
    pytest.importorskip("PySide6")

    import ai1_gen.gui.desktop.app as desktop_app

    monkeypatch.setattr(desktop_app, "RunOrchestrator", DummyDesktopOrchestrator)

    win = desktop_app.DesktopMainWindow()
    qtbot.addWidget(win)

    assert "AI1 Gen" in win.windowTitle()
    assert win.current_run_id is None


def test_desktop_build_run_input(qtbot, monkeypatch):
    pytest.importorskip("PySide6")

    import ai1_gen.gui.desktop.app as desktop_app

    monkeypatch.setattr(desktop_app, "RunOrchestrator", DummyDesktopOrchestrator)

    win = desktop_app.DesktopMainWindow()
    qtbot.addWidget(win)

    win.config_path_edit.setText("configs/default.yaml")
    win.out_root_edit.setText("D:/desktop_out")
    win.pages_spin.setValue(10)
    win.workers_spin.setValue(2)
    win.seed_spin.setValue(123)

    run_input = win.build_run_input()

    assert run_input.config_path.replace("\\", "/").endswith("configs/default.yaml")
    assert run_input.out_root.replace("\\", "/").endswith("D:/desktop_out")
    assert run_input.pages == 10
    assert run_input.workers == 2
    assert run_input.seed == 123
    assert isinstance(run_input.overrides, dict)


def test_desktop_start_run_updates_state(qtbot, monkeypatch):
    pytest.importorskip("PySide6")

    import ai1_gen.gui.desktop.app as desktop_app

    monkeypatch.setattr(desktop_app, "RunOrchestrator", DummyDesktopOrchestrator)

    win = desktop_app.DesktopMainWindow()
    qtbot.addWidget(win)

    win.config_path_edit.setText("configs/default.yaml")
    win.out_root_edit.setText("D:/desktop_out")
    win.pages_spin.setValue(10)
    win.workers_spin.setValue(2)
    win.seed_spin.setValue(123)

    def instant_worker(fn, on_success, on_error=None):
        try:
            on_success(fn())
        except Exception as e:
            if on_error:
                on_error(str(e))
            else:
                raise

    win.run_in_worker = instant_worker


    win.start_run()

    assert win.current_run_id == "desktop-run-123"
    assert win.run_id_label.text() == "desktop-run-123"
    assert win.state_label.text() in {"running", "done"}
    assert win.orchestrator.started_req is not None


def test_desktop_stop_run_calls_orchestrator(qtbot, monkeypatch):
    pytest.importorskip("PySide6")

    import ai1_gen.gui.desktop.app as desktop_app

    monkeypatch.setattr(desktop_app, "RunOrchestrator", DummyDesktopOrchestrator)

    win = desktop_app.DesktopMainWindow()
    qtbot.addWidget(win)

    win.current_run_id = "desktop-run-123"
    
    def instant_worker(fn, on_success, on_error=None):
        try:
            on_success(fn())
        except Exception as e:
            if on_error:
                on_error(str(e))
            else:
                raise

    win.run_in_worker = instant_worker
    
    win.stop_run()

    assert win.orchestrator.cancelled_run_id == "desktop-run-123"


def test_desktop_refresh_status_updates_labels(qtbot, monkeypatch):
    pytest.importorskip("PySide6")

    import ai1_gen.gui.desktop.app as desktop_app

    monkeypatch.setattr(desktop_app, "RunOrchestrator", DummyDesktopOrchestrator)

    win = desktop_app.DesktopMainWindow()
    qtbot.addWidget(win)

    win.current_run_id = "desktop-run-123"
    win.refresh_status()

    assert win.run_id_label.text() == "desktop-run-123"
    assert win.state_label.text() == "done"
    assert win.pid_label.text() == "222"
    assert win.return_code_label.text() == "0"
    assert win.out_root_label.text() == "D:/desktop_out"
    assert win.progress_label.text() == "finished"