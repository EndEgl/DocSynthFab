# src/ai1_gen/gui/web/simple_controls.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - nicegui>=2.0,<3.0

from __future__ import annotations

from typing import Any, Dict

from ai1_gen.gui.shared.override_utils import (
    clamp_percent,
    density_percent_to_dist,
    gap_percent_to_px,
    merge_maps,
    normalize_content_mix,
    placement_search_percent_to_attempts,
    spacing_percent_to_line_gap_scale,
)
from ai1_gen.gui.web.presets import (
    DATASET_CHARACTER_PRESETS,
    DATASET_GOAL_PRESETS,
    DIVERSITY_STRENGTH_PRESETS,
    DOCUMENT_TEMPLATE_PRESETS,
    TEXT_LENGTH_PRESETS,
)
from ai1_gen.gui.web.state import WebGuiState


CONTENT_MIX_PRESETS: Dict[str, Dict[str, float] | None] = {
    "Karışık belge": {"text": 60.0, "table": 25.0, "latex": 15.0},
    "Metin ağırlıklı": {"text": 85.0, "table": 15.0, "latex": 0.0},
    "Tablo ağırlıklı": {"text": 30.0, "table": 70.0, "latex": 0.0},
    "Sadece metin": {"text": 100.0, "table": 0.0, "latex": 0.0},
    "Sadece tablo": {"text": 0.0, "table": 100.0, "latex": 0.0},
    "Sadece LaTeX": {"text": 0.0, "table": 0.0, "latex": 100.0},
    "Özel": None,
}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def current_content_mix(state: WebGuiState) -> Dict[str, float]:
    preset_name = (
        str(state.content_mix_preset_select.value or "Karışık belge")
        if state.content_mix_preset_select is not None
        else "Karışık belge"
    )

    preset = CONTENT_MIX_PRESETS.get(preset_name)

    if preset is not None:
        return normalize_content_mix(
            preset.get("text", 0.0),
            preset.get("table", 0.0),
            preset.get("latex", 0.0),
        )

    return normalize_content_mix(
        state.text_mix_input.value if state.text_mix_input is not None else 60,
        state.table_mix_input.value if state.table_mix_input is not None else 25,
        state.latex_mix_input.value if state.latex_mix_input is not None else 15,
    )


def content_mix_label(state: WebGuiState) -> str:
    preset_name = (
        str(state.content_mix_preset_select.value or "Karışık belge")
        if state.content_mix_preset_select is not None
        else "Karışık belge"
    )

    raw_total = 0.0

    for widget in (state.text_mix_input, state.table_mix_input, state.latex_mix_input):
        if widget is not None:
            raw_total += _as_float(widget.value, 0.0)

    mix = current_content_mix(state)

    if preset_name != "Özel":
        return (
            f"Kullanılacak karışım: Text {mix['text']:.0f}%, "
            f"Table {mix['table']:.0f}%, LaTeX {mix['latex']:.0f}%"
        )

    return (
        f"Raw total: {raw_total:.0f} -> normalized: "
        f"Text {mix['text']:.0f}%, Table {mix['table']:.0f}%, "
        f"LaTeX {mix['latex']:.0f}%"
    )


def sync_custom_mix_visibility(state: WebGuiState) -> None:
    if state.custom_content_mix_panel is None or state.content_mix_preset_select is None:
        return

    is_custom = str(state.content_mix_preset_select.value or "") == "Özel"

    try:
        state.custom_content_mix_panel.visible = is_custom
        state.custom_content_mix_panel.update()
    except Exception:
        pass


def collect_simple_overrides(state: WebGuiState) -> Dict[str, Any]:
    if state.dataset_goal_select is None:
        return {}

    goal = str(state.dataset_goal_select.value or "Quick OCR Dataset")
    character = str(state.dataset_character_select.value or "Balanced")

    text_length = (
        str(state.text_length_select.value or "Balanced blocks")
        if state.text_length_select is not None
        else "Balanced blocks"
    )

    diversity_strength = (
        str(state.diversity_strength_select.value or "Balanced diversity")
        if state.diversity_strength_select is not None
        else "Balanced diversity"
    )

    document_template = (
        str(state.document_template_select.value or "Generic random document")
        if state.document_template_select is not None
        else "Generic random document"
    )

    mix = current_content_mix(state)

    density_percent = (
        state.density_percent_input.value
        if state.density_percent_input is not None
        else 50
    )

    spacing_percent = (
        state.line_gap_tolerance_input.value
        if state.line_gap_tolerance_input is not None
        else 0
    )

    whitespace_strategy = (
        str(state.whitespace_strategy_select.value or "balanced")
        if state.whitespace_strategy_select is not None
        else "balanced"
    )

    spread_percent = (
        clamp_percent(state.spread_percent_input.value, 65.0)
        if state.spread_percent_input is not None
        else 65.0
    )

    min_gap_px = (
        gap_percent_to_px(state.block_gap_percent_input.value)
        if state.block_gap_percent_input is not None
        else 12
    )

    max_place_attempts = (
        placement_search_percent_to_attempts(state.placement_search_percent_input.value)
        if state.placement_search_percent_input is not None
        else 48
    )

    overrides = merge_maps(
        DOCUMENT_TEMPLATE_PRESETS.get(document_template, {}),
        DATASET_GOAL_PRESETS.get(goal, {}),
        DATASET_CHARACTER_PRESETS.get(character, {}),
        TEXT_LENGTH_PRESETS.get(text_length, {}),
        DIVERSITY_STRENGTH_PRESETS.get(diversity_strength, {}),
        {
            "content.block_mix": mix,
            "dist.density_dist": density_percent_to_dist(density_percent),
            "layout.line_gap_random_scale": spacing_percent_to_line_gap_scale(spacing_percent),
            "layout.occupancy.enable": True,
            "layout.occupancy.whitespace_strategy": whitespace_strategy,
            "layout.occupancy.spread_percent": spread_percent,
            "layout.occupancy.min_gap_px": min_gap_px,
            "layout.occupancy.max_place_attempts": max_place_attempts,
        },
    )

    if state.content_source_mode_select is not None:
        mode = str(state.content_source_mode_select.value or "content_bank")
        overrides["content.source_mode"] = mode

        if mode == "random_chars":
            overrides["content.text_mode"] = "chars"

    latex_enabled = (
        bool(state.latex_render_enable_switch.value)
        if state.latex_render_enable_switch is not None
        else True
    )

    latex_base_url = (
        str(state.latex_http_base_url_input.value or "").strip()
        if state.latex_http_base_url_input is not None
        else ""
    )

    overrides["render.latex.enable"] = latex_enabled

    if latex_base_url:
        overrides["render.latex.http_base_url"] = latex_base_url

    return overrides