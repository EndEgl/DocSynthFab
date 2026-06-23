# src/docsynthfab/gui/web/run_state.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from docsynthfab.gui.shared.paths import ACTIVE_RUN_STATE_PATH

from .constants import TERMINAL_RUN_STATES
from .live_events import append_gui_event
from .state import WebGuiState


def is_unknown_run_error(e: Exception) -> bool:
    text = repr(e)
    return "orch/unknown-run-id" in text or "unknown-run-id" in text


def write_active_run_state(
    *,
    run_id: str,
    state: str = "running",
    out_root: str = "",
    config_path: str = "",
) -> None:
    try:
        ACTIVE_RUN_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "run_id": str(run_id),
            "state": str(state),
            "out_root": str(out_root or ""),
            "config_path": str(config_path or ""),
        }

        ACTIVE_RUN_STATE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    except Exception:
        pass


def read_active_run_state() -> Dict[str, Any]:
    try:
        if not ACTIVE_RUN_STATE_PATH.exists():
            return {}

        return json.loads(ACTIVE_RUN_STATE_PATH.read_text(encoding="utf-8"))

    except Exception:
        return {}


def clear_active_run_state() -> None:
    try:
        if ACTIVE_RUN_STATE_PATH.exists():
            ACTIVE_RUN_STATE_PATH.unlink()
    except Exception:
        pass


def reset_lost_run_state(state: WebGuiState, reason: str) -> None:
    lost_run_id = str(state.current_run_id or "-")

    state.current_run_id = None
    state.last_unknown_run_id = lost_run_id

    clear_active_run_state()

    try:
        if state.state_label is not None:
            state.state_label.text = "idle"
        if state.run_id_label is not None:
            state.run_id_label.text = "-"
        if state.pid_label is not None:
            state.pid_label.text = "-"
        if state.return_code_label is not None:
            state.return_code_label.text = "-"
        if state.out_root_label is not None:
            state.out_root_label.text = "-"
        if state.progress_label is not None:
            state.progress_label.text = "lost run state cleared"
        if state.start_btn is not None:
            state.start_btn.enable()
        if state.stop_btn is not None:
            state.stop_btn.disable()
    except Exception:
        pass

    append_gui_event(
        state,
        f"Cleared stale active run state. lost_run_id={lost_run_id}. reason={reason}",
        level="WARN",
    )


def restore_active_run_from_disk(state: WebGuiState) -> Optional[str]:
    data = read_active_run_state()
    run_id = str(data.get("run_id") or "").strip()

    if not run_id:
        append_gui_event(state, "No active run state found on disk.", level="INFO")
        return None

    state.current_run_id = run_id

    try:
        status = state.orchestrator.get_status(run_id)

        append_gui_event(
            state,
            f"Restored active run from disk: run_id={run_id}, "
            f"state={status.state}, out_root={getattr(status, 'out_root', '-')}",
            level="INFO",
        )

        return run_id

    except Exception as e:
        if is_unknown_run_error(e):
            reset_lost_run_state(state, repr(e))
            return None

        append_gui_event(
            state,
            f"Could not validate restored run_id={run_id}; keeping it for safety. error={repr(e)}",
            level="ERROR",
        )
        return run_id


def current_run_is_active(state: WebGuiState) -> bool:
    if not state.current_run_id:
        return False

    try:
        status = state.orchestrator.get_status(state.current_run_id)

        if status.state in TERMINAL_RUN_STATES:
            clear_active_run_state()
            return False

        return True

    except Exception as e:
        if is_unknown_run_error(e):
            reset_lost_run_state(state, repr(e))
            return False

        return True



