# test/unit/gui/test_web_start_run_request_contract.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - nicegui>=2.0,<3.0

from __future__ import annotations

from typing import Any

import pytest

import docsynthfab.gui.web.app as web_mod
from docsynthfab.gui.web.state import WebGuiState
from docsynthfab.orchestrator import RunRequest


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

    def set_text(self, text: str) -> None:
        self.text = str(text)

    def set_content(self, value: Any) -> None:
        self.value = value


class CapturingOrchestrator:
    def __init__(self) -> None:
        self.started_req = None

    def start(self, req):
        self.started_req = req
        return "unit-web-run-1"


def make_state() -> WebGuiState:
    state = WebGuiState()
    state.orchestrator = CapturingOrchestrator()

    state.config_path_input = DummyWidget("configs/default.yaml")
    state.out_root_input = DummyWidget("D:/web_out")
    state.pages_input = DummyWidget(7)
    state.workers_input = DummyWidget(2)
    state.seed_input = DummyWidget(1234)
    state.smoke_test_input = DummyWidget(False)

    state.raw_yaml_override_input = DummyWidget(
        """
content:
  block_mix:
    text: 11
    table: 22
    latex: 67
layout:
  occupancy:
    whitespace_strategy: compact
"""
    )

    state.start_btn = DummyWidget()
    state.stop_btn = DummyWidget()
    state.stop_btn.disable()

    state.run_id_label = DummyWidget(text="-")
    state.state_label = DummyWidget(text="idle")
    state.pid_label = DummyWidget(text="-")
    state.return_code_label = DummyWidget(text="-")
    state.out_root_label = DummyWidget(text="-")
    state.progress_label = DummyWidget(text="no active run")

    state.status_json = DummyWidget()
    state.summary_json = DummyWidget()
    state.stdout_log = DummyWidget()
    state.stderr_log = DummyWidget()

    # Simple dataset controls used by the real _collect_simple_overrides()
    state.dataset_goal_select = DummyWidget("Quick OCR Dataset")
    state.dataset_character_select = DummyWidget("Balanced")
    state.text_length_select = DummyWidget("Balanced blocks")
    state.diversity_strength_select = DummyWidget("Balanced diversity")
    state.document_template_select = DummyWidget("Generic random document")

    state.content_source_mode_select = DummyWidget("random_chars")

    state.content_mix_preset_select = DummyWidget("Custom")
    state.text_mix_input = DummyWidget(85)
    state.table_mix_input = DummyWidget(10)

    state.density_percent_input = DummyWidget(70)
    state.line_gap_tolerance_input = DummyWidget(25)

    state.whitespace_strategy_select = DummyWidget("spread")
    state.spread_percent_input = DummyWidget(80)
    state.block_gap_percent_input = DummyWidget(30)
    state.placement_search_percent_input = DummyWidget(90)

    # Advanced/schema widgets are intentionally empty in this unit test.
    state.field_widgets = {}

    return state


def patch_start_run_side_effects(monkeypatch) -> None:
    """
    Unit tests in this file verify Web GUI -> RunRequest contract.

    They must not depend on:
    - NiceGUI notifications
    - active-run disk state
    - real status refresh
    - Docker / LaTeX HTTP renderer availability

    The real LaTeX preflight is covered by integration/E2E tests.
    """

    monkeypatch.setattr(web_mod, "current_run_is_active", lambda _state: False)
    monkeypatch.setattr(web_mod, "_refresh_status", lambda _state: None)
    monkeypatch.setattr(web_mod, "write_active_run_state", lambda **kwargs: None)
    monkeypatch.setattr(web_mod, "safe_notify", lambda *args, **kwargs: None)

    # If web.app imports these functions into module scope, patch them there.
    monkeypatch.setattr(
        web_mod,
        "ensure_http_renderer_ready_once",
        lambda *args, **kwargs: None,
        raising=False,
    )
    monkeypatch.setattr(
        web_mod,
        "check_latex_http_health",
        lambda *args, **kwargs: None,
        raising=False,
    )

    # If _start_run imports from docsynthfab.latex.http_render inside the function,
    # patch the source module as well.
    try:
        import docsynthfab.latex.http_render as http_render

        monkeypatch.setattr(
            http_render,
            "ensure_http_renderer_ready_once",
            lambda *args, **kwargs: None,
            raising=False,
        )
        monkeypatch.setattr(
            http_render,
            "check_latex_http_health",
            lambda *args, **kwargs: None,
            raising=False,
        )
    except Exception:
        pass


def test_web_start_run_uses_actual_state_values_without_nicegui(monkeypatch):
    state = make_state()
    patch_start_run_side_effects(monkeypatch)

    # Burada _collect_all_overrides_for_run monkeypatch edilmez.
    # Dummy widget value'ları gerçek collect fonksiyonundan geçer.

    web_mod._start_run(state)

    req = state.orchestrator.started_req

    assert req is not None
    assert req.pages == 7
    assert req.workers == 2
    assert req.seed == 1234

    mix = req.overrides["content.block_mix"]

    assert mix["text"] == pytest.approx(89.4737)
    assert mix["table"] == pytest.approx(10.5263)
    assert mix["latex"] == 0.0

    assert req.overrides["content.source_mode"] == "random_chars"
    assert req.overrides["content.text_mode"] == "chars"
    assert req.overrides["layout.occupancy.enable"] is True
    assert req.overrides["layout.occupancy.whitespace_strategy"] == "balanced"

    assert req.raw_yaml_override_text.strip()



def test_web_start_run_uses_actual_state_values_without_nicegui(monkeypatch):
    state = make_state()
    patch_start_run_side_effects(monkeypatch)

    # Burada _collect_all_overrides_for_run monkeypatch edilmez.
    # Dummy widget value'ları gerçek collect fonksiyonundan geçer.

    web_mod._start_run(state)

    req = state.orchestrator.started_req

    assert req is not None
    assert req.pages == 7
    assert req.workers == 2
    assert req.seed == 1234

    mix = req.overrides["content.block_mix"]

    assert mix["text"] == pytest.approx(89.4737)
    assert mix["table"] == pytest.approx(10.5263)
    assert mix["latex"] == 0.0

    assert req.overrides["content.source_mode"] == "random_chars"
    assert req.overrides["content.text_mode"] == "chars"
    assert req.overrides["layout.occupancy.enable"] is True
    assert req.overrides["layout.occupancy.whitespace_strategy"] == "balanced"

    assert req.raw_yaml_override_text.strip()



def test_web_start_is_blocked_when_run_is_active(monkeypatch):
    state = make_state()
    state.current_run_id = "run-web-1"
    state.state_label.text = "running"

    notified = {"value": False}

    monkeypatch.setattr(web_mod, "current_run_is_active", lambda _state: True)
    monkeypatch.setattr(
        web_mod,
        "safe_notify",
        lambda *args, **kwargs: notified.__setitem__("value", True),
    )

    web_mod._start_run(state)

    assert state.orchestrator.started_req is None
    assert notified["value"] is True



