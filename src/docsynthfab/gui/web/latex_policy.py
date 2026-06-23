# src/docsynthfab/gui/web/latex_policy.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import Any, Dict

from docsynthfab.gui.shared.override_utils import normalize_content_mix
from docsynthfab.gui.web.live_events import append_gui_event, safe_notify
from docsynthfab.gui.web.state import WebGuiState


LATEX_MISSING_BEHAVIORS = [
    "LaTeX'i kapat ve devam et",
    "Run'ı durdur",
]


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def latex_mix_from_overrides(overrides: Dict[str, Any]) -> float:
    mix = overrides.get("content.block_mix", {}) or {}

    if not isinstance(mix, dict):
        return 0.0

    return _as_float(mix.get("latex", 0.0), 0.0)


def latex_requested_from_overrides(overrides: Dict[str, Any]) -> bool:
    latex_ratio = latex_mix_from_overrides(overrides)
    latex_enabled = bool(overrides.get("render.latex.enable", True))

    return latex_ratio > 0.0 and latex_enabled


def disable_latex_in_overrides(overrides: Dict[str, Any]) -> None:
    mix = dict(overrides.get("content.block_mix", {}) or {})

    text = _as_float(mix.get("text", 0.0), 0.0)
    table = _as_float(mix.get("table", 0.0), 0.0)

    if text <= 0.0 and table <= 0.0:
        text = 100.0
        table = 0.0

    normalized = normalize_content_mix(text, table, 0.0)

    overrides["content.block_mix"] = {
        "text": normalized["text"],
        "table": normalized["table"],
        "latex": 0.0,
    }
    overrides["render.latex.enable"] = False


def prepare_latex_or_fallback(
    state: WebGuiState,
    overrides: Dict[str, Any],
) -> bool:
    """
    Prepare LaTeX renderer when LaTeX is requested.

    Returns:
        True  -> continue starting run
        False -> block starting run

    Default UX policy:
    - If LaTeX is not requested, do nothing.
    - If LaTeX is requested and renderer is ready, continue.
    - If renderer is not ready:
        - default behavior: disable LaTeX and continue
        - optional behavior: block run
    """
    if not latex_requested_from_overrides(overrides):
        return True

    try:
        from docsynthfab.latex.http_render import (
            DEFAULT_HTTP_BASE_URL,
            ensure_http_renderer_ready_once,
        )

        latex_base_url = str(
            overrides.get("render.latex.http_base_url")
            or overrides.get("latex.http_base_url")
            or DEFAULT_HTTP_BASE_URL
            or "http://127.0.0.1:8080"
        ).rstrip("/")

        ensure_http_renderer_ready_once(http_base_url=latex_base_url)

        append_gui_event(
            state,
            f"LaTeX renderer is ready: {latex_base_url}",
            level="INFO",
        )

        if state.latex_status_label is not None:
            state.latex_status_label.text = f"Renderer hazır: {latex_base_url}"
            try:
                state.latex_status_label.update()
            except Exception:
                pass

        return True

    except Exception as e:
        behavior = (
            str(state.latex_missing_behavior_select.value or "LaTeX'i kapat ve devam et")
            if state.latex_missing_behavior_select is not None
            else "LaTeX'i kapat ve devam et"
        )

        if behavior == "Run'ı durdur":
            append_gui_event(
                state,
                (
                    "Start blocked: LaTeX renderer is required but not ready. "
                    f"reason={e!r}"
                ),
                level="ERROR",
            )
            safe_notify(
                state,
                "LaTeX renderer hazır değil. Run durduruldu.",
                color="negative",
                level="ERROR",
            )
            return False

        disable_latex_in_overrides(overrides)

        append_gui_event(
            state,
            (
                "LaTeX renderer is not ready. "
                "Continuing with LaTeX disabled. "
                f"reason={e!r}"
            ),
            level="WARN",
        )

        safe_notify(
            state,
            "LaTeX renderer hazır değil. LaTeX kapatılarak üretime devam ediliyor.",
            color="warning",
            level="WARN",
        )

        if state.latex_status_label is not None:
            state.latex_status_label.text = "Renderer hazır değil; LaTeX kapatıldı."
            try:
                state.latex_status_label.update()
            except Exception:
                pass

        return True



