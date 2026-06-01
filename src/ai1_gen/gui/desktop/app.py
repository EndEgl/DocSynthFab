# src/ai1_gen/gui/desktop/app.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - PySide6>=6.5,<7.0
# - PyYAML>=6.0,<7.0
#
# Final modular desktop GUI for AI1 Gen.
#
# Design:
# - This file is the desktop GUI entrypoint.
# - It uses RunOrchestrator directly.
# - It does not import or depend on the web GUI app.
# - It reuses shared path/config helpers and web preset dictionaries.
# - Long or IO-sensitive orchestrator calls run in worker threads.

from __future__ import annotations

import json
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QDoubleSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# If this file is run directly, add the src root to sys.path.
_THIS_FILE = Path(__file__).resolve()

# Current file:
#   .../src/ai1_gen/gui/desktop/app.py
#
# Therefore:
#   _PKG_DIR      = .../src/ai1_gen
#   _SRC_ROOT     = .../src
#   _PROJECT_ROOT = .../ai1_gen
_PKG_DIR = _THIS_FILE.parents[2]
_SRC_ROOT = _THIS_FILE.parents[3]
_PROJECT_ROOT = _THIS_FILE.parents[4]

if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from ai1_gen.orchestrator import RunOrchestrator, RunRequest
from ai1_gen.orchestrator.result_store import tail_text

from ai1_gen.gui.shared.override_utils import (
    clamp_percent,
    density_percent_to_dist,
    gap_percent_to_px,
    merge_maps,
    normalize_content_mix,
    placement_search_percent_to_attempts,
    spacing_percent_to_line_gap_scale,
)
from ai1_gen.gui.shared.paths import (
    DEFAULT_CONFIG,
    normalize_config_path,
    normalize_out_root,
    open_path,
)
from ai1_gen.gui.web.presets import (
    DATASET_CHARACTER_PRESETS,
    DATASET_GOAL_PRESETS,
    DIVERSITY_STRENGTH_PRESETS,
    DOCUMENT_TEMPLATE_PRESETS,
    TEXT_LENGTH_PRESETS,
)


TERMINAL_RUN_STATES = {"done", "failed", "cancelled"}


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


@dataclass
class DesktopRunInput:
    config_path: str
    out_root: str
    pages: int
    workers: int
    seed: int
    smoke_test: bool
    overrides: Dict[str, Any]


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    @Slot()
    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception:
            self.failed.emit(traceback.format_exc())


class DesktopMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.orchestrator = RunOrchestrator()
        self.current_run_id: Optional[str] = None
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[Worker] = None

        self.setWindowTitle("AI1 Gen Desktop GUI")
        self.resize(1280, 820)

        self._build_ui()

        self.status_timer = QTimer(self)
        self.status_timer.setInterval(2000)
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start()

        self.refresh_effective_yaml_preview()

    # -----------------------------------------------------
    # UI construction
    # -----------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)

        splitter = QSplitter()
        root_layout.addWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([520, 760])

        left_layout.addWidget(self._build_run_group())
        left_layout.addWidget(self._build_preset_group())
        left_layout.addWidget(self._build_action_group())
        left_layout.addStretch(1)

        right_layout.addWidget(self._build_status_tabs())

        self.setCentralWidget(root)

    def _build_run_group(self) -> QGroupBox:
        box = QGroupBox("Run")
        layout = QFormLayout(box)

        self.config_path_edit = QLineEdit(str(DEFAULT_CONFIG))
        config_row = QWidget()
        config_row_layout = QHBoxLayout(config_row)
        config_row_layout.setContentsMargins(0, 0, 0, 0)
        config_row_layout.addWidget(self.config_path_edit)
        browse_cfg_btn = QPushButton("Browse")
        browse_cfg_btn.clicked.connect(self.browse_config)
        config_row_layout.addWidget(browse_cfg_btn)
        layout.addRow("Config path", config_row)

        self.out_root_edit = QLineEdit("out/desktop_gui_run")
        out_row = QWidget()
        out_row_layout = QHBoxLayout(out_row)
        out_row_layout.setContentsMargins(0, 0, 0, 0)
        out_row_layout.addWidget(self.out_root_edit)
        browse_out_btn = QPushButton("Browse")
        browse_out_btn.clicked.connect(self.browse_output_root)
        out_row_layout.addWidget(browse_out_btn)
        layout.addRow("Output root", out_row)

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 1_000_000)
        self.pages_spin.setValue(20)
        layout.addRow("Pages", self.pages_spin)

        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 256)
        self.workers_spin.setValue(2)
        layout.addRow("Workers", self.workers_spin)

        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 2_147_483_647)
        self.seed_spin.setValue(1337)
        layout.addRow("Seed", self.seed_spin)

        self.smoke_checkbox = QCheckBox("Smoke test")
        layout.addRow("", self.smoke_checkbox)

        for widget in (
            self.config_path_edit,
            self.out_root_edit,
            self.pages_spin,
            self.workers_spin,
            self.seed_spin,
            self.smoke_checkbox,
        ):
            if hasattr(widget, "textChanged"):
                widget.textChanged.connect(self.refresh_effective_yaml_preview)
            elif hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self.refresh_effective_yaml_preview)
            elif hasattr(widget, "stateChanged"):
                widget.stateChanged.connect(self.refresh_effective_yaml_preview)

        return box

    def _build_preset_group(self) -> QGroupBox:
        box = QGroupBox("Dataset controls")
        layout = QFormLayout(box)

        self.dataset_goal_combo = QComboBox()
        self.dataset_goal_combo.addItems(list(DATASET_GOAL_PRESETS.keys()))
        layout.addRow("Dataset goal", self.dataset_goal_combo)

        self.dataset_character_combo = QComboBox()
        self.dataset_character_combo.addItems(list(DATASET_CHARACTER_PRESETS.keys()))
        self.dataset_character_combo.setCurrentText("Balanced")
        layout.addRow("Visual character", self.dataset_character_combo)

        self.text_length_combo = QComboBox()
        self.text_length_combo.addItems(list(TEXT_LENGTH_PRESETS.keys()))
        self.text_length_combo.setCurrentText("Balanced blocks")
        layout.addRow("Text length", self.text_length_combo)

        self.diversity_strength_combo = QComboBox()
        self.diversity_strength_combo.addItems(list(DIVERSITY_STRENGTH_PRESETS.keys()))
        self.diversity_strength_combo.setCurrentText("Balanced diversity")
        layout.addRow("Diversity strength", self.diversity_strength_combo)

        self.document_template_combo = QComboBox()
        self.document_template_combo.addItems(list(DOCUMENT_TEMPLATE_PRESETS.keys()))
        self.document_template_combo.setCurrentText("Generic random document")
        layout.addRow("Document template", self.document_template_combo)

        self.content_mode_combo = QComboBox()
        self.content_mode_combo.addItems(["content_bank", "random_chars"])
        layout.addRow("Content source", self.content_mode_combo)

        self.text_mix_spin = QDoubleSpinBox()
        self.text_mix_spin.setRange(0.0, 100.0)
        self.text_mix_spin.setValue(60.0)
        self.text_mix_spin.setSingleStep(1.0)
        layout.addRow("Text %", self.text_mix_spin)

        self.table_mix_spin = QDoubleSpinBox()
        self.table_mix_spin.setRange(0.0, 100.0)
        self.table_mix_spin.setValue(25.0)
        self.table_mix_spin.setSingleStep(1.0)
        layout.addRow("Table %", self.table_mix_spin)

        self.latex_mix_spin = QDoubleSpinBox()
        self.latex_mix_spin.setRange(0.0, 100.0)
        self.latex_mix_spin.setValue(15.0)
        self.latex_mix_spin.setSingleStep(1.0)
        layout.addRow("LaTeX %", self.latex_mix_spin)

        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.0, 100.0)
        self.density_spin.setValue(50.0)
        self.density_spin.setSingleStep(1.0)
        layout.addRow("Density %", self.density_spin)

        self.line_gap_spin = QDoubleSpinBox()
        self.line_gap_spin.setRange(0.0, 100.0)
        self.line_gap_spin.setValue(0.0)
        self.line_gap_spin.setSingleStep(1.0)
        layout.addRow("Line spacing randomness %", self.line_gap_spin)

        self.whitespace_strategy_combo = QComboBox()
        self.whitespace_strategy_combo.addItems(["balanced", "spread", "compact"])
        layout.addRow("Whitespace strategy", self.whitespace_strategy_combo)

        self.spread_spin = QDoubleSpinBox()
        self.spread_spin.setRange(0.0, 100.0)
        self.spread_spin.setValue(65.0)
        self.spread_spin.setSingleStep(1.0)
        layout.addRow("Spread %", self.spread_spin)

        self.block_gap_spin = QDoubleSpinBox()
        self.block_gap_spin.setRange(0.0, 100.0)
        self.block_gap_spin.setValue(20.0)
        self.block_gap_spin.setSingleStep(1.0)
        layout.addRow("Block gap %", self.block_gap_spin)

        self.placement_search_spin = QDoubleSpinBox()
        self.placement_search_spin.setRange(0.0, 100.0)
        self.placement_search_spin.setValue(45.0)
        self.placement_search_spin.setSingleStep(1.0)
        layout.addRow("Placement search %", self.placement_search_spin)

        for widget in (
            self.dataset_goal_combo,
            self.dataset_character_combo,
            self.text_length_combo,
            self.diversity_strength_combo,
            self.document_template_combo,
            self.content_mode_combo,
        ):
            widget.currentTextChanged.connect(self.refresh_effective_yaml_preview)

        for widget in (
            self.text_mix_spin,
            self.table_mix_spin,
            self.latex_mix_spin,
            self.density_spin,
            self.line_gap_spin,
            self.spread_spin,
            self.block_gap_spin,
            self.placement_search_spin,
        ):
            widget.valueChanged.connect(self.refresh_effective_yaml_preview)

        self.whitespace_strategy_combo.currentTextChanged.connect(self.refresh_effective_yaml_preview)

        return box

    def _build_action_group(self) -> QGroupBox:
        box = QGroupBox("Actions")
        layout = QGridLayout(box)

        self.start_button = QPushButton("Start run")
        self.start_button.clicked.connect(self.start_run)
        layout.addWidget(self.start_button, 0, 0)

        self.stop_button = QPushButton("Stop run")
        self.stop_button.clicked.connect(self.stop_run)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button, 0, 1)

        refresh_button = QPushButton("Refresh status")
        refresh_button.clicked.connect(self.refresh_status)
        layout.addWidget(refresh_button, 1, 0)

        open_output_button = QPushButton("Open output")
        open_output_button.clicked.connect(self.open_output)
        layout.addWidget(open_output_button, 1, 1)

        return box

    def _build_status_tabs(self) -> QTabWidget:
        tabs = QTabWidget()

        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)

        self.run_id_label = QLabel("-")
        self.state_label = QLabel("idle")
        self.pid_label = QLabel("-")
        self.return_code_label = QLabel("-")
        self.out_root_label = QLabel("-")
        self.progress_label = QLabel("no active run")

        form = QFormLayout()
        form.addRow("Run ID", self.run_id_label)
        form.addRow("State", self.state_label)
        form.addRow("PID", self.pid_label)
        form.addRow("Return code", self.return_code_label)
        form.addRow("Output root", self.out_root_label)
        form.addRow("Progress", self.progress_label)
        status_layout.addLayout(form)

        self.status_json_edit = QPlainTextEdit()
        self.status_json_edit.setReadOnly(True)
        status_layout.addWidget(self.status_json_edit)

        tabs.addTab(status_widget, "Status")

        self.summary_json_edit = QPlainTextEdit()
        self.summary_json_edit.setReadOnly(True)
        tabs.addTab(self.summary_json_edit, "Summary")

        self.stdout_edit = QPlainTextEdit()
        self.stdout_edit.setReadOnly(True)
        tabs.addTab(self.stdout_edit, "stdout")

        self.stderr_edit = QPlainTextEdit()
        self.stderr_edit.setReadOnly(True)
        tabs.addTab(self.stderr_edit, "stderr")

        self.effective_yaml_edit = QPlainTextEdit()
        self.effective_yaml_edit.setReadOnly(True)
        tabs.addTab(self.effective_yaml_edit, "Effective YAML")

        self.raw_yaml_override_edit = QTextEdit()
        self.raw_yaml_override_edit.setPlaceholderText("Optional raw YAML override")
        self.raw_yaml_override_edit.textChanged.connect(self.refresh_effective_yaml_preview)
        tabs.addTab(self.raw_yaml_override_edit, "Raw YAML override")

        self.event_log_edit = QPlainTextEdit()
        self.event_log_edit.setReadOnly(True)
        tabs.addTab(self.event_log_edit, "Events")

        return tabs

    # -----------------------------------------------------
    # Path actions
    # -----------------------------------------------------

    def browse_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select config YAML",
            str(_PROJECT_ROOT),
            "YAML files (*.yaml *.yml);;All files (*.*)",
        )

        if path:
            self.config_path_edit.setText(path)

    def browse_output_root(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select output root",
            str(_PROJECT_ROOT),
        )

        if path:
            self.out_root_edit.setText(path)

    def open_output(self) -> None:
        out_root = self.out_root_label.text().strip()

        if not out_root or out_root == "-":
            QMessageBox.warning(self, "No output", "No output root is available yet.")
            return

        try:
            open_path(out_root)
        except Exception as e:
            QMessageBox.critical(self, "Open output failed", str(e))

    # -----------------------------------------------------
    # Overrides / request
    # -----------------------------------------------------

    def collect_overrides(self) -> Dict[str, Any]:
        goal = self.dataset_goal_combo.currentText()
        character = self.dataset_character_combo.currentText()
        text_length = self.text_length_combo.currentText()
        diversity_strength = self.diversity_strength_combo.currentText()
        document_template = self.document_template_combo.currentText()

        mix = normalize_content_mix(
            self.text_mix_spin.value(),
            self.table_mix_spin.value(),
            self.latex_mix_spin.value(),
        )

        density_percent = self.density_spin.value()
        spacing_percent = self.line_gap_spin.value()
        whitespace_strategy = self.whitespace_strategy_combo.currentText()
        spread_percent = clamp_percent(self.spread_spin.value(), 65.0)
        min_gap_px = gap_percent_to_px(self.block_gap_spin.value())
        max_place_attempts = placement_search_percent_to_attempts(
            self.placement_search_spin.value()
        )

        overrides = merge_maps(
            DOCUMENT_TEMPLATE_PRESETS.get(document_template, {}),
            DATASET_GOAL_PRESETS.get(goal, {}),
            DATASET_CHARACTER_PRESETS.get(character, {}),
            TEXT_LENGTH_PRESETS.get(text_length, {}),
            DIVERSITY_STRENGTH_PRESETS.get(diversity_strength, {}),
            {
                "content.block_mix": mix,
                "dist.density_dist": density_percent_to_dist(density_percent),
                "layout.line_gap_random_scale": spacing_percent_to_line_gap_scale(spacing_percent),
                "layout.occupancy.enable": True,
                "layout.occupancy.whitespace_strategy": whitespace_strategy,
                "layout.occupancy.spread_percent": spread_percent,
                "layout.occupancy.min_gap_px": min_gap_px,
                "layout.occupancy.max_place_attempts": max_place_attempts,
            },
        )

        mode = self.content_mode_combo.currentText()
        overrides["content.source_mode"] = mode

        if mode == "random_chars":
            overrides["content.text_mode"] = "chars"

        return overrides

    def build_run_input(self) -> DesktopRunInput:
        return DesktopRunInput(
            config_path=normalize_config_path(self.config_path_edit.text()),
            out_root=normalize_out_root(self.out_root_edit.text()),
            pages=self.pages_spin.value(),
            workers=self.workers_spin.value(),
            seed=self.seed_spin.value(),
            smoke_test=self.smoke_checkbox.isChecked(),
            overrides=self.collect_overrides(),
        )

    def refresh_effective_yaml_preview(self) -> None:
        try:
            run_input = self.build_run_input()
            raw_yaml = self.raw_yaml_override_edit.toPlainText() if hasattr(self, "raw_yaml_override_edit") else ""

            text = self.orchestrator.build_effective_config_yaml_text(
                config_path=run_input.config_path,
                overrides=run_input.overrides,
                raw_yaml_override_text=raw_yaml,
                out_root=run_input.out_root,
                pages=run_input.pages,
                workers=run_input.workers,
                seed=run_input.seed,
                smoke_test=run_input.smoke_test,
            )

            if hasattr(self, "effective_yaml_edit"):
                self.effective_yaml_edit.setPlainText(text)

        except Exception as e:
            if hasattr(self, "effective_yaml_edit"):
                self.effective_yaml_edit.setPlainText(f"# preview error\n{e}")

    # -----------------------------------------------------
    # Worker helpers
    # -----------------------------------------------------

    def run_in_worker(self, fn, on_success, on_error=None) -> None:
        if self._worker_thread is not None:
            QMessageBox.warning(self, "Busy", "Another background operation is still running.")
            return

        thread = QThread(self)
        worker = Worker(fn)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(on_success)

        if on_error is None:
            worker.failed.connect(self.show_worker_error)
        else:
            worker.failed.connect(on_error)

        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_worker_refs)

        self._worker_thread = thread
        self._worker = worker

        thread.start()

    @Slot()
    def _clear_worker_refs(self) -> None:
        self._worker_thread = None
        self._worker = None

    @Slot(str)
    def show_worker_error(self, error_text: str) -> None:
        self.append_event("ERROR", error_text)
        QMessageBox.critical(self, "Worker error", error_text)

    # -----------------------------------------------------
    # Run lifecycle
    # -----------------------------------------------------

    def start_run(self) -> None:
        if self.current_run_id and self.state_label.text() not in TERMINAL_RUN_STATES:
            QMessageBox.warning(self, "Run active", "A run is already active.")
            return

        run_input = self.build_run_input()
        raw_yaml = self.raw_yaml_override_edit.toPlainText()

        request = RunRequest(
            config_path=run_input.config_path,
            out_root=run_input.out_root,
            pages=run_input.pages,
            workers=run_input.workers,
            seed=run_input.seed,
            smoke_test=run_input.smoke_test,
            overrides=run_input.overrides,
            raw_yaml_override_text=raw_yaml,
        )

        def job() -> str:
            return self.orchestrator.start(request)

        def ok(run_id: str) -> None:
            self.current_run_id = str(run_id)
            self.run_id_label.setText(str(run_id))
            self.state_label.setText("running")
            self.out_root_label.setText(run_input.out_root or "-")
            self.progress_label.setText("run started")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.append_event("INFO", f"Run started: {run_id}")
            self.refresh_status()

        def err(error_text: str) -> None:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.append_event("ERROR", error_text)
            QMessageBox.critical(self, "Run start failed", error_text)

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.append_event(
            "INFO",
            (
                "Starting run with "
                f"config={run_input.config_path}, "
                f"out_root={run_input.out_root}, "
                f"pages={run_input.pages}, "
                f"workers={run_input.workers}, "
                f"seed={run_input.seed}, "
                f"override_keys={sorted(run_input.overrides.keys())}"
            ),
        )

        self.run_in_worker(job, ok, err)



    def stop_run(self) -> None:
        if not self.current_run_id:
            QMessageBox.warning(self, "No run", "No active run to stop.")
            return

        run_id = self.current_run_id

        def job() -> bool:
            return bool(self.orchestrator.cancel(run_id))

        def ok(cancelled: bool) -> None:
            if cancelled:
                self.append_event("WARN", f"Run cancelled: {run_id}")
            else:
                self.append_event("WARN", f"Run could not be cancelled: {run_id}")

            self.refresh_status()

        self.run_in_worker(job, ok)

    def refresh_status(self) -> None:
        if not self.current_run_id:
            self.run_id_label.setText("-")
            self.state_label.setText("idle")
            self.pid_label.setText("-")
            self.return_code_label.setText("-")
            self.progress_label.setText("no active run")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.refresh_event_log()
            return

        run_id = self.current_run_id

        try:
            status = self.orchestrator.get_status(run_id)
            status_obj = status.to_dict()

            self.run_id_label.setText(status.run_id)
            self.state_label.setText(status.state)
            self.pid_label.setText(str(status.pid) if status.pid is not None else "-")
            self.return_code_label.setText(
                str(status.return_code) if status.return_code is not None else "-"
            )
            self.out_root_label.setText(status.out_root or "-")

            if status.progress is not None:
                self.progress_label.setText(status.progress.message or status.state)
            else:
                self.progress_label.setText(status.state)

            self.status_json_edit.setPlainText(_json_dumps(status_obj))

            if status.stdout_log:
                self.stdout_edit.setPlainText(tail_text(status.stdout_log, 16000))

            if status.stderr_log:
                self.stderr_edit.setPlainText(tail_text(status.stderr_log, 16000))

            try:
                summary = self.orchestrator.get_summary(run_id)
                self.summary_json_edit.setPlainText(_json_dumps(summary.to_dict()))
            except Exception:
                pass

            if status.state in TERMINAL_RUN_STATES:
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
            else:
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)

        except Exception as e:
            self.append_event("ERROR", f"Status refresh failed: {e}")

        self.refresh_event_log()

    # -----------------------------------------------------
    # Events
    # -----------------------------------------------------

    def append_event(self, level: str, message: str) -> None:
        line = f"[{level}] {message}"
        current = self.event_log_edit.toPlainText()
        self.event_log_edit.setPlainText((current + "\n" + line).strip())

    def refresh_event_log(self) -> None:
        # Desktop keeps its own visible event pane for now.
        # If you later want shared disk logging, connect this to GUI_EVENT_LOG_PATH.
        pass


def main() -> None:
    app = QApplication(sys.argv)
    window = DesktopMainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()