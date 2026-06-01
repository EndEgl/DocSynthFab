# test/e2e/test_15_web_gui_option_matrix_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - nicegui>=2.0,<3.0

from __future__ import annotations

import os
import re
import threading
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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


def _slug(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "_", text.strip())
    return text.strip("_").lower()


def prepare_case_output_dir(base: Path, case_name: str) -> Path:
    keep = os.environ.get("AI1_E2E_KEEP_OUTPUTS", "").strip() == "1"

    if keep:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = base / f"{_slug(case_name)}_{stamp}"
        out.mkdir(parents=True, exist_ok=True)
        return out

    return fresh_output_dir(base / _slug(case_name))


def make_state(
    *,
    config_path: Path,
    out_root: Path,
    pages: int,
    workers: int,
    seed: int,
    content_source: str,
    text_mix: float,
    table_mix: float,
    latex_mix: float,
    dataset_goal: str = "Quick OCR Dataset",
    visual_character: str = "Balanced",
    text_length: str = "Balanced blocks",
    diversity_strength: str = "Balanced diversity",
    document_template: str = "Generic random document",
    density: float = 50,
    line_gap_randomness: float = 0,
    whitespace_strategy: str = "balanced",
    spread: float = 65,
    block_gap: float = 20,
    placement_search: float = 45,
    raw_yaml: str = "",
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
        raw_yaml_override_input=DummyWidget(raw_yaml),

        dataset_goal_select=DummyWidget(dataset_goal),
        dataset_character_select=DummyWidget(visual_character),
        text_length_select=DummyWidget(text_length),
        diversity_strength_select=DummyWidget(diversity_strength),
        document_template_select=DummyWidget(document_template),

        content_source_mode_select=DummyWidget(content_source),
        text_mix_input=DummyWidget(text_mix),
        table_mix_input=DummyWidget(table_mix),
        latex_mix_input=DummyWidget(latex_mix),

        density_percent_input=DummyWidget(density),
        line_gap_tolerance_input=DummyWidget(line_gap_randomness),
        whitespace_strategy_select=DummyWidget(whitespace_strategy),
        spread_percent_input=DummyWidget(spread),
        block_gap_percent_input=DummyWidget(block_gap),
        placement_search_percent_input=DummyWidget(placement_search),

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
    parts: list[str] = [
        f"out_root={out_root}",
        f"run_id={state.current_run_id}",
        f"state_label={getattr(state.state_label, 'text', '')}",
        f"progress_label={getattr(state.progress_label, 'text', '')}",
        f"return_code_label={getattr(state.return_code_label, 'text', '')}",
        f"image_count={len(list((out_root / 'images').glob('*.png'))) if (out_root / 'images').exists() else 0}",
    ]

    for path in [
        out_root / "run.log",
        out_root / "errors.jsonl",
        out_root / "failed_pages.log",
        out_root / "gt_pages.jsonl",
        out_root / "reports" / "run_manifest.json",
    ]:
        parts.append(f"\n--- {path} ---")
        parts.append(read_text_safe(path)[-8000:] if path.exists() else "<missing>")

    if state.current_run_id:
        run_dir = state.orchestrator.work_root / str(state.current_run_id)
        parts.append(f"\n--- run_dir={run_dir} ---")

        for name in ["stdout.log", "stderr.log", "effective_config.yaml"]:
            path = run_dir / name
            parts.append(f"\n--- {path} ---")
            parts.append(read_text_safe(path)[-8000:] if path.exists() else "<missing>")

    return "\n".join(parts)


WEB_GUI_CASES = [
    {
        "name": "text_only_random_chars_w1",
        "pages": 3,
        "workers": 1,
        "content_source": "random_chars",
        "mix": (100, 0, 0),
    },
    {
        "name": "text_only_random_chars_w4",
        "pages": 8,
        "workers": 4,
        "content_source": "random_chars",
        "mix": (100, 0, 0),
    },
    {
        "name": "text_table_random_chars_w4",
        "pages": 8,
        "workers": 4,
        "content_source": "random_chars",
        "mix": (70, 30, 0),
    },
    {
        "name": "balanced_content_bank_no_latex_w2",
        "pages": 5,
        "workers": 2,
        "content_source": "content_bank",
        "mix": (75, 25, 0),
    },
]

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.parametrize("case", WEB_GUI_CASES, ids=[c["name"] for c in WEB_GUI_CASES])
def test_web_gui_option_matrix_generates_images(
    case: dict[str, Any],
    e2e_default_config: Path,
    e2e_out_root: Path,
    monkeypatch,
):
    pytest.importorskip("nicegui")

    import ai1_gen.gui.web.app as web_app

    out_root = prepare_case_output_dir(
        e2e_out_root / "web_gui_option_matrix",
        case["name"],
    )

    text_mix, table_mix, latex_mix = case["mix"]

    state = make_state(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=int(case["pages"]),
        workers=int(case["workers"]),
        seed=20260530,
        content_source=str(case["content_source"]),
        text_mix=float(text_mix),
        table_mix=float(table_mix),
        latex_mix=float(latex_mix),
    )

    monkeypatch.setattr(web_app, "current_run_is_active", lambda _state: False)
    monkeypatch.setattr(web_app, "write_active_run_state", lambda **kwargs: None)
    monkeypatch.setattr(web_app, "clear_active_run_state", lambda: None)
    monkeypatch.setattr(web_app, "safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(web_app, "refresh_live_event_log", lambda _state: None)

    web_app._start_run(state)

    assert state.current_run_id, (
        "web _start_run did not create a run_id\n\n"
        + diagnostics(out_root, state)
    )

    try:
        status = wait_for_run(
            state.orchestrator,
            state.current_run_id,
            timeout_s=420.0,
        )
    except Exception as exc:
        pytest.fail(
            f"Web GUI case did not finish: {case['name']}\n"
            f"{exc!r}\n\n"
            + diagnostics(out_root, state)
        )

    web_app._refresh_status(state)

    assert str(getattr(status, "state", "")) in {"done", "completed"}, (
        f"Web GUI case did not complete cleanly: {case['name']} status={status!r}\n\n"
        + diagnostics(out_root, state)
    )

    assert_output_package_exists(out_root)

    counts = assert_page_counts_match(out_root, expected_pages=int(case["pages"]))

    assert counts["image_count"] == int(case["pages"]), (
        f"Wrong image count for case={case['name']}\n\n"
        + diagnostics(out_root, state)
    )