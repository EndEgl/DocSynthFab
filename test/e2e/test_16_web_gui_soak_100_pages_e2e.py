# test/e2e/test_16_web_gui_soak_100_pages_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - nicegui>=2.0,<3.0

from __future__ import annotations

import os
from pathlib import Path

import pytest

from test_15_web_gui_option_matrix_e2e import (
    diagnostics,
    make_state,
    prepare_case_output_dir,
)

from e2e_support import (
    assert_output_package_exists,
    assert_page_counts_match,
    wait_for_run,
)


@pytest.mark.e2e
@pytest.mark.slow
def test_web_gui_non_latex_100_pages_generates_images(
    e2e_default_config: Path,
    e2e_out_root: Path,
    monkeypatch,
):
    """
    Long web-GUI soak contract without LaTeX dependency.

    Purpose:
    - Prove Web GUI -> RunOrchestrator -> CLI subprocess can generate 100 pages.
    - Prove workers=4 is stable for a longer run.
    - Do NOT depend on the external LaTeX renderer.

    LaTeX has its own required-renderer tests.
    """
    if os.environ.get("AI1_E2E_RUN_SOAK", "").strip() != "1":
        pytest.skip("Set AI1_E2E_RUN_SOAK=1 to run the 100-page web GUI soak test.")

    pytest.importorskip("nicegui")

    import ai1_gen.gui.web.app as web_app

    out_root = prepare_case_output_dir(
        e2e_out_root / "web_gui_soak",
        "non_latex_100_pages_w4",
    )

    state = make_state(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=100,
        workers=4,
        seed=1337,
        content_source="content_bank",

        # Important:
        # This is the long stability test, not the LaTeX renderer test.
        text_mix=75,
        table_mix=25,
        latex_mix=0,

        density=50,
        line_gap_randomness=0,
        whitespace_strategy="balanced",
        spread=65,
        block_gap=20,
        placement_search=45,
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
            timeout_s=1800.0,
        )
    except Exception as exc:
        pytest.fail(
            f"100-page non-LaTeX soak run did not finish.\n{exc!r}\n\n"
            + diagnostics(out_root, state)
        )

    web_app._refresh_status(state)

    assert str(getattr(status, "state", "")) in {"done", "completed"}, (
        f"100-page non-LaTeX soak run did not complete cleanly: {status!r}\n\n"
        + diagnostics(out_root, state)
    )

    assert_output_package_exists(out_root)

    counts = assert_page_counts_match(out_root, expected_pages=100)

    assert counts["image_count"] == 100, (
        "100-page non-LaTeX web GUI soak run produced wrong image count.\n\n"
        + diagnostics(out_root, state)
    )