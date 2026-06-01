# test/e2e/test_13_web_start_run_multiprocess_output_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - nicegui>=2.0,<3.0

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
import threading

import pytest

from ai1_gen.orchestrator import RunOrchestrator

from e2e_support import (
    assert_output_package_exists,
    assert_page_counts_match,
    fresh_output_dir,
    read_text_safe,
    wait_for_run,
)


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


def make_state(
    *,
    config_path: Path,
    out_root: Path,
    pages: int,
    workers: int,
    seed: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        run_lock=threading.Lock(),
        current_run_id=None,
        last_unknown_run_id=None,
        last_status_log_signature=None,
        orchestrator=RunOrchestrator(),

        config_path_input=DummyWidget(str(config_path)),
        out_root_input=DummyWidget(str(out_root)),
        pages_input=DummyWidget(pages),
        workers_input=DummyWidget(workers),
        seed_input=DummyWidget(seed),
        smoke_test_input=DummyWidget(False),
        raw_yaml_override_input=DummyWidget(""),

        dataset_goal_select=DummyWidget("Quick OCR Dataset"),
        dataset_character_select=DummyWidget("Balanced"),
        text_length_select=DummyWidget("Balanced blocks"),
        diversity_strength_select=DummyWidget("Balanced diversity"),
        document_template_select=DummyWidget("Generic random document"),

        content_source_mode_select=DummyWidget("random_chars"),
        text_mix_input=DummyWidget(100),
        table_mix_input=DummyWidget(0),
        latex_mix_input=DummyWidget(0),

        density_percent_input=DummyWidget(50),
        line_gap_tolerance_input=DummyWidget(0),
        whitespace_strategy_select=DummyWidget("balanced"),
        spread_percent_input=DummyWidget(65),
        block_gap_percent_input=DummyWidget(20),
        placement_search_percent_input=DummyWidget(45),

        field_widgets={},
        baseline_overrides={},
        csv_loading_mode=False,

        start_btn=DummyWidget(),
        stop_btn=DummyWidget(),

        run_id_label=DummyWidget(text="-"),
        state_label=DummyWidget(text="idle"),
        pid_label=DummyWidget(text="-"),
        return_code_label=DummyWidget(text="-"),
        out_root_label=DummyWidget(text="-"),
        progress_label=DummyWidget(text="no active run"),

        status_json=DummyWidget(value="{}"),
        summary_json=DummyWidget(value="{}"),
        stdout_log=DummyWidget(value=""),
        stderr_log=DummyWidget(value=""),
        live_event_log=DummyWidget(value=""),
        live_event_status_label=DummyWidget(text="-"),
    )


def diagnostics(out_root: Path, state: SimpleNamespace) -> str:
    parts = [
        f"out_root={out_root}",
        f"run_id={state.current_run_id}",
        f"state_label={getattr(state.state_label, 'text', '')}",
        f"progress_label={getattr(state.progress_label, 'text', '')}",
        f"return_code_label={getattr(state.return_code_label, 'text', '')}",
    ]

    for path in [
        out_root / "run.log",
        out_root / "errors.jsonl",
        out_root / "failed_pages.log",
        out_root / "gt_pages.jsonl",
        out_root / "reports" / "run_manifest.json",
    ]:
        parts.append(f"\n--- {path} ---")
        parts.append(read_text_safe(path)[-5000:] if path.exists() else "<missing>")

    if state.current_run_id:
        run_dir = state.orchestrator.work_root / str(state.current_run_id)
        parts.append(f"\n--- run_dir={run_dir} ---")

        for name in ["stdout.log", "stderr.log", "effective_config.yaml"]:
            path = run_dir / name
            parts.append(f"\n--- {path} ---")
            parts.append(read_text_safe(path)[-5000:] if path.exists() else "<missing>")

    return "\n".join(parts)


@pytest.mark.e2e
@pytest.mark.slow
def test_web_start_run_multiprocess_generates_images(
    e2e_default_config: Path,
    e2e_out_root: Path,
    monkeypatch,
):
    pytest.importorskip("nicegui")

    import ai1_gen.gui.web.app as web_app

    out_root = fresh_output_dir(e2e_out_root / "web_start_multiprocess_output")

    state = make_state(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=8,
        workers=4,
        seed=20260529,
    )

    monkeypatch.setattr(web_app, "current_run_is_active", lambda _state: False)
    monkeypatch.setattr(web_app, "write_active_run_state", lambda **kwargs: None)
    monkeypatch.setattr(web_app, "clear_active_run_state", lambda: None)
    monkeypatch.setattr(web_app, "safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(web_app, "refresh_live_event_log", lambda _state: None)

    web_app._start_run(state)

    assert state.current_run_id, "web _start_run did not create a run_id"

    try:
        status = wait_for_run(state.orchestrator, state.current_run_id, timeout_s=240.0)
    except Exception as exc:
        pytest.fail(
            "Web-started multiprocess run did not finish.\n"
            f"{exc!r}\n\n"
            + diagnostics(out_root, state)
        )

    web_app._refresh_status(state)

    assert str(getattr(status, "state", "")) in {"done", "completed"}, (
        f"Run did not complete cleanly: {status!r}\n\n"
        + diagnostics(out_root, state)
    )

    assert_output_package_exists(out_root)

    counts = assert_page_counts_match(out_root, expected_pages=8)

    assert counts["image_count"] == 8, (
        "Multiprocess web-started run produced wrong image count.\n\n"
        + diagnostics(out_root, state)
    )