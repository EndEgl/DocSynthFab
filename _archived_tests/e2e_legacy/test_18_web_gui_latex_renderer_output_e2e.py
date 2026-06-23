# test/e2e/test_18_web_gui_latex_renderer_output_e2e.py
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
def test_web_gui_latex_renderer_generates_images(
    e2e_default_config: Path,
    e2e_out_root: Path,
    monkeypatch,
):
    """
    Real LaTeX renderer output contract.

    This test should run only when the external LaTeX renderer is actually ready.

    Required env:
    - AI1_E2E_RUN_LATEX=1
    - AI1_LATEX_HTTP_BASE_URL=http://127.0.0.1:18080
    """
    if os.environ.get("AI1_E2E_RUN_LATEX", "").strip() != "1":
        pytest.skip("Set AI1_E2E_RUN_LATEX=1 to run the real LaTeX renderer E2E test.")

    pytest.importorskip("nicegui")

    import docsynthfab.gui.web.app as web_app
    from docsynthfab.latex.http_render import (
        DEFAULT_HTTP_BASE_URL,
        check_latex_http_health,
    )

    latex_base_url = os.environ.get("AI1_LATEX_HTTP_BASE_URL", DEFAULT_HTTP_BASE_URL)

    try:
        check_latex_http_health(latex_base_url, timeout_s=2)
    except Exception as exc:
        pytest.skip(f"LaTeX renderer is not ready at {latex_base_url}: {exc!r}")

    out_root = prepare_case_output_dir(
        e2e_out_root / "web_gui_latex",
        "latex_renderer_output_w2",
    )

    state = make_state(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=6,
        workers=2,
        seed=20260530,
        content_source="random_chars",

        # This is the actual LaTeX production test.
        text_mix=80,
        table_mix=0,
        latex_mix=20,

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
        "web _start_run did not create a run_id even though LaTeX renderer is healthy\n\n"
        + diagnostics(out_root, state)
    )

    try:
        status = wait_for_run(
            state.orchestrator,
            state.current_run_id,
            timeout_s=600.0,
        )
    except Exception as exc:
        pytest.fail(
            f"LaTeX renderer run did not finish.\n{exc!r}\n\n"
            + diagnostics(out_root, state)
        )

    web_app._refresh_status(state)

    assert str(getattr(status, "state", "")) in {"done", "completed"}, (
        f"LaTeX renderer run did not complete cleanly: {status!r}\n\n"
        + diagnostics(out_root, state)
    )

    assert_output_package_exists(out_root)

    counts = assert_page_counts_match(out_root, expected_pages=6)

    assert counts["image_count"] == 6, (
        "LaTeX renderer web GUI run produced wrong image count.\n\n"
        + diagnostics(out_root, state)
    )



