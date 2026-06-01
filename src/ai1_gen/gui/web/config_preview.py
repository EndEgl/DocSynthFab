# src/ai1_gen/gui/web/config_preview.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import json
from typing import Any, Dict

from ai1_gen.gui.shared.paths import normalize_config_path, normalize_out_root
from ai1_gen.gui.shared.override_utils import lookup_nested_value

from .state import WebGuiState


def read_widget_value(
    schema_map: Dict[str, Dict[str, Any]],
    field_key: str,
    widget: Any,
) -> Any:
    field = schema_map.get(field_key, {})
    field_type = field.get("field_type", "str")

    if field_type == "bool":
        return bool(widget.value)

    if field_type == "enum":
        return widget.value

    if field_type == "int":
        try:
            return int(widget.value)
        except Exception:
            return 0

    if field_type == "float":
        try:
            return float(widget.value)
        except Exception:
            return 0.0

    txt = str(widget.value or "").strip()

    if field_type in {"json", "color_rgb"}:
        try:
            return json.loads(txt)
        except Exception:
            return txt

    return txt


def collect_overrides(
    state: WebGuiState,
    schema_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    for key, widget in state.field_widgets.items():
        value = read_widget_value(schema_map, key, widget)
        field = schema_map.get(key, {})
        field_type = field.get("field_type", "str")

        if field_type == "json" and value == {}:
            continue
        if field_type == "path" and str(value or "").strip() == "":
            continue
        if field_type == "str" and str(value or "").strip() == "":
            continue

        out[key] = value

    return out


def build_current_effective_yaml(
    state: WebGuiState,
    *,
    overrides: Dict[str, Any],
) -> str:
    config_path = normalize_config_path(str(state.config_path_input.value or ""))
    out_root = normalize_out_root(str(state.out_root_input.value or ""))

    raw_yaml_text = ""
    if state.raw_yaml_override_input is not None:
        raw_yaml_text = str(state.raw_yaml_override_input.value or "")

    return state.orchestrator.build_effective_config_yaml_text(
        config_path=config_path,
        overrides=overrides,
        raw_yaml_override_text=raw_yaml_text,
        out_root=out_root,
        pages=int(state.pages_input.value or 0),
        workers=int(state.workers_input.value or 0),
        seed=int(state.seed_input.value or -1),
        smoke_test=bool(state.smoke_test_input.value),
    )


def refresh_effective_yaml_preview(
    state: WebGuiState,
    *,
    overrides: Dict[str, Any],
) -> None:
    if state.effective_yaml_preview is None:
        return

    try:
        state.effective_yaml_preview.value = build_current_effective_yaml(
            state,
            overrides=overrides,
        )
    except Exception as e:
        state.effective_yaml_preview.value = f"# preview error\n{e}"


def load_form_from_override_map(
    state: WebGuiState,
    schema_map: Dict[str, Dict[str, Any]],
    override_map: Dict[str, Any],
) -> None:
    for key, widget in state.field_widgets.items():
        value = override_map.get(key, schema_map.get(key, {}).get("default"))

        try:
            field = schema_map.get(key, {})
            field_type = field.get("field_type", "str")

            if field_type == "bool":
                widget.value = bool(value)

            elif field_type == "enum":
                choices = field.get("choices", []) or []
                widget.value = value if value in choices else (choices[0] if choices else None)

            elif field_type == "int":
                widget.value = int(value if value is not None else 0)

            elif field_type == "float":
                widget.value = float(value if value is not None else 0.0)

            else:
                if field_type in {"json", "color_rgb"}:
                    widget.value = json.dumps(value if value is not None else {}, ensure_ascii=False)
                else:
                    widget.value = "" if value is None else str(value)

        except Exception:
            pass


def load_baseline_and_user_config(
    state: WebGuiState,
    schema_map: Dict[str, Dict[str, Any]],
) -> None:
    config_path = normalize_config_path(str(state.config_path_input.value or ""))

    state.baseline_overrides = state.orchestrator.build_baseline_override_map(
        config_path,
        visibility="advanced",
    )

    merged_cfg = state.orchestrator.build_config_with_user_override(
        config_path=config_path,
        overrides=None,
        raw_yaml_override_text=None,
    )

    current_map = dict(state.baseline_overrides)

    for key in current_map.keys():
        current_map[key] = lookup_nested_value(
            merged_cfg,
            key,
            state.baseline_overrides.get(key),
        )

    load_form_from_override_map(state, schema_map, current_map)

    if state.user_yaml_path_label is not None:
        state.user_yaml_path_label.text = str(state.orchestrator.get_user_config_path(config_path))

    if state.raw_yaml_override_input is not None:
        state.raw_yaml_override_input.value = ""