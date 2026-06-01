# test/e2e/test_03_desktop_gui_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - PySide6>=6.5,<7.0
# - pytest-qt>=4.4,<5.0

from __future__ import annotations

from pathlib import Path

import pytest

from acceptance_report import append_metric_record
from e2e_support import (
    assert_no_fatal_log_errors,
    assert_output_package_exists,
    fresh_output_dir,
    wait_for_run,
)
from quality_metrics import measure_all_core_metrics


@pytest.mark.e2e
@pytest.mark.slow
def test_desktop_gui_full_generation_e2e(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
    qtbot,
):
    pytest.importorskip("PySide6")

    import ai1_gen.gui.desktop.app as desktop_mod
    from ai1_gen.orchestrator import RunRequest

    out_root = fresh_output_dir(e2e_out_root / "desktop_gui_full_generation")

    win = desktop_mod.DesktopMainWindow()
    qtbot.addWidget(win)

    win.config_path_edit.setText(str(e2e_default_config))
    win.out_root_edit.setText(str(out_root))
    win.pages_spin.setValue(3)
    win.workers_spin.setValue(1)
    win.seed_spin.setValue(123)
    win.smoke_checkbox.setChecked(False)

    win.text_mix_spin.setValue(60.0)
    win.table_mix_spin.setValue(25.0)
    win.latex_mix_spin.setValue(15.0)

    run_input = win.build_run_input()

    assert run_input.config_path.endswith("default.yaml")
    assert run_input.pages == 3
    assert run_input.workers == 1
    assert run_input.seed == 123
    assert isinstance(run_input.overrides, dict)

    req = RunRequest(
        config_path=run_input.config_path,
        out_root=run_input.out_root,
        pages=run_input.pages,
        workers=run_input.workers,
        seed=run_input.seed,
        smoke_test=run_input.smoke_test,
        overrides={
            **run_input.overrides,
            "run.export_targets": ["native", "segformer", "coco"],
        },
    )

    run_id = win.orchestrator.start(req)
    status = wait_for_run(win.orchestrator, run_id, timeout_s=240.0)

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    assert_output_package_exists(out_root)
    assert_no_fatal_log_errors(out_root)

    metrics = measure_all_core_metrics(out_root)
    metrics["interface"] = "desktop_gui"
    metrics["request_build_score"] = 1.0
    metrics["override_count"] = len(run_input.overrides)

    append_metric_record(
        project_root=project_root,
        test_name="test_desktop_gui_full_generation_e2e",
        metrics=metrics,
    )

    assert metrics["package_score"] == 1.0
    assert metrics["manifest_score"] == 1.0
    assert metrics["bbox_valid_ratio"] == 1.0