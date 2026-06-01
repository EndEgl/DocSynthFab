# test/e2e/test_17_web_gui_latex_required_preflight_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - nicegui>=2.0,<3.0

from __future__ import annotations

from pathlib import Path

import pytest

from test_15_web_gui_option_matrix_e2e import (
    diagnostics,
    make_state,
    prepare_case_output_dir,
)


@pytest.mark.e2e
def test_web_gui_latex_required_blocks_when_renderer_is_not_ready(
    e2e_default_config: Path,
    e2e_out_root: Path,
    monkeypatch,
):
    """
    LaTeX-required preflight contract.

    If LaTeX is requested but the renderer is not healthy, Web GUI must not
    start a backend run. This prevents the old bug where output folders were
    created but workers stayed stuck and images/*.png remained empty.
    """
    pytest.importorskip("nicegui")

    import ai1_gen.gui.web.app as web_app

    out_root = prepare_case_output_dir(
        e2e_out_root / "web_gui_latex_preflight",
        "latex_required_renderer_not_ready",
    )

    state = make_state(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=3,
        workers=2,
        seed=20260530,
        content_source="random_chars",
        text_mix=80,
        table_mix=0,
        latex_mix=20,
    )

    events: list[tuple[str, str]] = []
    notifications: list[tuple[tuple, dict]] = []

    def fake_append_gui_event(_state, message: str, level: str = "INFO") -> None:
        events.append((level, message))

    def fake_safe_notify(_state, *args, **kwargs) -> None:
        notifications.append((args, kwargs))

    def fake_health_check(*args, **kwargs) -> None:
        raise RuntimeError("synthetic latex renderer not ready")

    monkeypatch.setattr(web_app, "current_run_is_active", lambda _state: False)
    monkeypatch.setattr(web_app, "write_active_run_state", lambda **kwargs: None)
    monkeypatch.setattr(web_app, "clear_active_run_state", lambda: None)
    monkeypatch.setattr(web_app, "refresh_live_event_log", lambda _state: None)

    monkeypatch.setattr(web_app, "append_gui_event", fake_append_gui_event)
    monkeypatch.setattr(web_app, "safe_notify", fake_safe_notify)

    import ai1_gen.latex.http_render as http_render

    monkeypatch.setattr(http_render, "check_latex_http_health", fake_health_check)

    web_app._start_run(state)

    assert state.current_run_id is None, (
        "LaTeX-required run should not start when renderer is not ready.\n\n"
        + diagnostics(out_root, state)
    )

    assert not (out_root / "images").exists(), (
        "Output generation should not begin when LaTeX preflight blocks the run.\n\n"
        + diagnostics(out_root, state)
    )

    all_event_text = "\n".join(f"[{level}] {msg}" for level, msg in events).lower()
    all_notify_text = "\n".join(
        " ".join(str(x) for x in args) + " " + str(kwargs)
        for args, kwargs in notifications
    ).lower()

    assert "latex renderer" in all_event_text
    assert "not ready" in all_event_text
    assert "latex renderer" in all_notify_text or "not ready" in all_notify_text