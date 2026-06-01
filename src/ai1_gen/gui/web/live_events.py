# src/ai1_gen/gui/web/live_events.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - nicegui>=2.0,<3.0

from __future__ import annotations

from datetime import datetime

from nicegui import ui

from ai1_gen.gui.shared.paths import GUI_EVENT_LOG_PATH
from ai1_gen.orchestrator.result_store import tail_text

from .state import WebGuiState


def append_gui_event(state: WebGuiState, message: str, *, level: str = "INFO") -> None:
    """Append a GUI event to disk and to the live event panel."""
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level.upper()}] {message}"

        GUI_EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        with GUI_EVENT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

        if state.live_event_status_label is not None:
            state.live_event_status_label.text = line

        if state.live_event_log is not None:
            state.live_event_log.value = tail_text(str(GUI_EVENT_LOG_PATH), 16000)

    except Exception:
        # GUI logging must never crash the app.
        pass


def refresh_live_event_log(state: WebGuiState) -> None:
    try:
        if state.live_event_log is not None and GUI_EVENT_LOG_PATH.exists():
            state.live_event_log.value = tail_text(str(GUI_EVENT_LOG_PATH), 16000)
    except Exception:
        pass


def safe_notify(
    state: WebGuiState,
    message: str,
    *,
    color: str = "primary",
    level: str = "INFO",
) -> None:
    append_gui_event(state, message, level=level)

    try:
        ui.notify(message, color=color)
    except Exception:
        pass