# test/e2e/test_10_web_start_run_real_output_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - nicegui>=2.0,<3.0
# - PyYAML>=6.0,<7.0

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from docsynthfab.orchestrator import RunOrchestrator

from e2e_support import (
    assert_no_fatal_log_errors,
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


def make_web_e2e_state(
    *,
    config_path: Path,
    out_root: Path,
    pages: int = 1,
    workers: int = 1,
    seed: int = 123,
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

        # Minimal, robust generation profile:
        # text-only + random chars avoids LaTeX/table/content-bank edge cases.
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


def collect_diagnostics(*, out_root: Path, state: SimpleNamespace) -> str:
    parts: list[str] = []

    parts.append(f"out_root={out_root}")
    parts.append(f"current_run_id={state.current_run_id}")
    parts.append(f"state_label={getattr(state.state_label, 'text', None)}")
    parts.append(f"progress_label={getattr(state.progress_label, 'text', None)}")
    parts.append(f"return_code_label={getattr(state.return_code_label, 'text', None)}")

    images = (
        sorted((out_root / "images").glob("*.png"))
        if (out_root / "images").exists()
        else []
    )
    parts.append(f"image_count={len(images)}")

    interesting_files = [
        out_root / "run.log",
        out_root / "errors.jsonl",
        out_root / "failed_pages.log",
        out_root / "gt_pages.jsonl",
        out_root / "qc_summary.json",
        out_root / "reports" / "run_manifest.json",
    ]

    for path in interesting_files:
        parts.append("")
        parts.append(f"--- {path} ---")
        if path.exists():
            text = read_text_safe(path)
            parts.append(text[-4000:] if text else "<empty>")
        else:
            parts.append("<missing>")

    if state.current_run_id:
        run_dir = state.orchestrator.work_root / str(state.current_run_id)
        parts.append("")
        parts.append(f"--- run_dir={run_dir} ---")

        for name in ("stdout.log", "stderr.log", "effective_config.yaml"):
            path = run_dir / name
            parts.append("")
            parts.append(f"--- {path} ---")
            if path.exists():
                text = read_text_safe(path)
                parts.append(text[-4000:] if text else "<empty>")
            else:
                parts.append("<missing>")

    return "\n".join(parts)


@pytest.mark.e2e
@pytest.mark.slow
def test_web_start_run_real_output_generates_at_least_one_image(
    e2e_default_config: Path,
    e2e_out_root: Path,
    monkeypatch,
):
    """
    Web GUI production contract:

    Calling the web Start action handler must create a real backend run and
    produce at least one image.

    This catches the bug where output directories and worker _tmp folders are
    created but images/*.png remains empty.
    """
    pytest.importorskip("nicegui")

    import docsynthfab.gui.web.app as web_app

    out_root = fresh_output_dir(e2e_out_root / "web_start_real_output")

    state = make_web_e2e_state(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=1,
        workers=1,
        seed=20260529,
    )

    # Isolate this E2E from global active-run disk state.
    monkeypatch.setattr(web_app, "current_run_is_active", lambda _state: False)
    monkeypatch.setattr(web_app, "write_active_run_state", lambda **kwargs: None)
    monkeypatch.setattr(web_app, "clear_active_run_state", lambda: None)
    monkeypatch.setattr(web_app, "safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(web_app, "refresh_live_event_log", lambda _state: None)

    web_app._start_run(state)

    assert state.current_run_id, "web _start_run did not create a run_id"

    try:
        status = wait_for_run(
            state.orchestrator,
            state.current_run_id,
            timeout_s=180.0,
        )
    except Exception as exc:
        pytest.fail(
            "Web-started real run did not reach a terminal state.\n"
            f"{exc!r}\n\n"
            + collect_diagnostics(out_root=out_root, state=state)
        )

    web_app._refresh_status(state)

    state_value = str(getattr(status, "state", ""))

    assert state_value in {"done", "completed"}, (
        f"web-started run did not complete cleanly: {status!r}\n\n"
        + collect_diagnostics(out_root=out_root, state=state)
    )

    assert_output_package_exists(out_root)

    counts = assert_page_counts_match(out_root, expected_pages=1)

    assert counts["image_count"] >= 1, (
        "Web-started run completed but produced no images.\n\n"
        + collect_diagnostics(out_root=out_root, state=state)
    )

    assert_no_fatal_log_errors(out_root)



