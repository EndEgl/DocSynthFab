# test/e2e/test_02_web_gui_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - nicegui>=2.0,<3.0

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from acceptance_report import append_metric_record
from e2e_support import (
    assert_no_fatal_log_errors,
    assert_output_package_exists,
    fresh_output_dir,
    wait_for_run,
)
from quality_metrics import measure_all_core_metrics


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


@pytest.mark.e2e
@pytest.mark.slow
def test_web_gui_full_generation_e2e(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
    monkeypatch,
):
    pytest.importorskip("nicegui")

    import ai1_gen.gui.web.app as web_mod
    from ai1_gen.gui.web.state import WebGuiState
    from ai1_gen.orchestrator import RunOrchestrator

    out_root = fresh_output_dir(e2e_out_root / "web_gui_full_generation")

    state = WebGuiState()
    state.orchestrator = RunOrchestrator()

    state.config_path_input = DummyWidget(str(e2e_default_config))
    state.out_root_input = DummyWidget(str(out_root))
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

    monkeypatch.setattr(
        web_mod,
        "_collect_all_overrides_for_run",
        lambda _state: {
            "run.export_targets": ["native", "segformer", "coco"],
            "content.block_mix": {"text": 60, "table": 25, "latex": 15},
        },
    )
    monkeypatch.setattr(web_mod, "_refresh_status", lambda _state: None)
    monkeypatch.setattr(web_mod, "write_active_run_state", lambda **kwargs: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *a, **k: None)

    web_mod._start_run(state)

    assert state.current_run_id

    status = wait_for_run(state.orchestrator, state.current_run_id, timeout_s=240.0)
    assert str(getattr(status, "state", "")) in {"done", "completed"}

    assert_output_package_exists(out_root)
    assert_no_fatal_log_errors(out_root)

    metrics = measure_all_core_metrics(out_root)
    metrics["interface"] = "web_gui"
    metrics["request_build_score"] = 1.0

    append_metric_record(
        project_root=project_root,
        test_name="test_web_gui_full_generation_e2e",
        metrics=metrics,
    )

    assert metrics["package_score"] == 1.0
    assert metrics["manifest_score"] == 1.0
    assert metrics["bbox_valid_ratio"] == 1.0