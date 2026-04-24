from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QMessageBox

import ai1_gen.gui as gui_mod


class DummyOrchestrator:
    def __init__(self):
        self.started_req = None
        self.cancelled_run_id = None

    def get_schema_for_ui(self, mode=None):
        return []

    def start(self, req):
        self.started_req = req
        return "run-123"

    def cancel(self, run_id):
        self.cancelled_run_id = run_id
        return True

    def get_status(self, run_id):
        return SimpleNamespace(
            state="done",
            pid=111,
            return_code=0,
            out_root="D:/out",
            progress=SimpleNamespace(state="finished"),
            stdout_log="",
            stderr_log="",
        )

    def get_summary(self, run_id):
        return SimpleNamespace(
            to_dict=lambda: {"run_id": run_id, "state": "done"},
            out_root="D:/out",
            qc_summary_path="D:/out/qc_summary.json",
            run_log_path="D:/out/run.log",
        )


@pytest.fixture
def gui_window(qtbot, monkeypatch):
    monkeypatch.setattr(gui_mod, "RunOrchestrator", DummyOrchestrator)
    win = gui_mod.AI1GenGUI()
    qtbot.addWidget(win)
    return win


def test_gui_constructs_and_has_basic_state(gui_window):
    assert gui_window.windowTitle() == "AI1 Gen | Desktop GUI"
    assert gui_window.current_run_id is None
    assert gui_window.start_btn.isEnabled()
    assert not gui_window.stop_btn.isEnabled()


def test_gui_start_run_updates_state(gui_window):
    gui_window.config_path_edit.setText("configs/default.yaml")
    gui_window.out_root_edit.setText("D:/out")
    gui_window.pages_spin.setValue(10)
    gui_window.workers_spin.setValue(2)
    gui_window.seed_spin.setValue(123)

    gui_window._start_run()

    assert gui_window.current_run_id == "run-123"
    assert gui_window.run_id_label.text() == "run-123"
    assert gui_window.state_label.text() == "running"
    assert not gui_window.start_btn.isEnabled()
    assert gui_window.stop_btn.isEnabled()


def test_gui_stop_run_calls_orchestrator(gui_window):
    gui_window.current_run_id = "run-123"
    gui_window._stop_run()

    assert gui_window.orchestrator.cancelled_run_id == "run-123"
    assert gui_window.state_label.text() == "cancelled"
    assert gui_window.start_btn.isEnabled()
    assert not gui_window.stop_btn.isEnabled()


def test_gui_poll_run_updates_labels(gui_window):
    gui_window.current_run_id = "run-123"

    gui_window._poll_run()

    assert gui_window.state_label.text() == "done"
    assert gui_window.pid_label.text() == "111"
    assert gui_window.return_code_label.text() == "0"
    assert gui_window.out_root_label.text() == "D:/out"
    assert gui_window.progress_label.text() == "finished"