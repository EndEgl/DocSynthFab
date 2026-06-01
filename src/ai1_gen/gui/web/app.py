# src/ai1_gen/gui/web/app.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - nicegui>=2.0,<3.0
# - PyYAML>=6.0,<7.0

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


# If this file is run directly, add the src root to sys.path.
_THIS_FILE = Path(__file__).resolve()

# Current file:
#   .../src/ai1_gen/gui/web/app.py
#
# Therefore:
#   _PKG_DIR      = .../src/ai1_gen
#   _SRC_ROOT     = .../src
#   _PROJECT_ROOT = .../ai1_gen
_PKG_DIR = _THIS_FILE.parents[2]
_SRC_ROOT = _THIS_FILE.parents[3]
_PROJECT_ROOT = _THIS_FILE.parents[4]

# Web GUI must always run from the project root.
try:
    os.chdir(_PROJECT_ROOT)
except Exception:
    pass

if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))


from nicegui import ui

from ai1_gen.gui.web.simple_controls import (
    CONTENT_MIX_PRESETS,
    collect_simple_overrides,
    content_mix_label,
    current_content_mix,
    sync_custom_mix_visibility,
)
from ai1_gen.gui.web.latex_policy import (
    LATEX_MISSING_BEHAVIORS,
    prepare_latex_or_fallback,
)

from ai1_gen.orchestrator import RunRequest
from ai1_gen.orchestrator.result_store import tail_text



from ai1_gen.gui.shared.override_utils import (
    clamp_percent,
    content_mix_preview_label,
    density_percent_to_dist,
    density_preview_label,
    gap_percent_to_px,
    merge_maps,
    normalize_content_mix,
    placement_search_percent_to_attempts,
    spacing_percent_to_line_gap_scale,
    table_amount_preview_label,
)
from ai1_gen.gui.shared.paths import (
    DEFAULT_CONFIG,
    GUI_EVENT_LOG_PATH,
    normalize_config_path,
    normalize_out_root,
    open_path,
)

from ai1_gen.gui.web.config_preview import (
    collect_overrides,
    load_baseline_and_user_config,
    refresh_effective_yaml_preview,
)
from ai1_gen.gui.web.content_actions import (
    ensure_custom_content_csvs,
    reset_content_csvs,
    save_uploaded_content_csv,
)
from ai1_gen.gui.web.live_events import append_gui_event, refresh_live_event_log, safe_notify
from ai1_gen.gui.web.presets import (
    DATASET_CHARACTER_PRESETS,
    DATASET_GOAL_PRESETS,
    DIVERSITY_STRENGTH_PRESETS,
    DOCUMENT_TEMPLATE_PRESETS,
    TEXT_LENGTH_PRESETS,
    TEMPLATE_REGION_TYPES,
)
from ai1_gen.gui.web.run_state import (
    clear_active_run_state,
    current_run_is_active,
    restore_active_run_from_disk,
    write_active_run_state,
)
from ai1_gen.gui.web.state import WEB_STATE, WebGuiState
from ai1_gen.gui.web.template_csv import (
    active_template_rows,
    available_template_names,
    export_template_csv_example,
    handle_template_csv_upload,
    open_template_csv,
)

STATE = WEB_STATE
TERMINAL_RUN_STATES = {"done", "failed", "cancelled"}

try:
    SCHEMA_MAP: Dict[str, Dict[str, Any]] = {
        f["key"]: f for f in STATE.orchestrator.get_schema_for_ui()
    }
except Exception:
    SCHEMA_MAP = {}


# ---------------------------------------------------------
# Small value helpers
# ---------------------------------------------------------

def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _set_text(widget: Any, value: Any) -> None:
    if widget is not None:
        widget.text = str(value)


def _set_value(widget: Any, value: Any) -> None:
    if widget is not None:
        widget.value = value


def _safe_update(widget: Any) -> None:
    try:
        if widget is not None:
            widget.update()
    except Exception:
        pass


# ---------------------------------------------------------
# Override collection
# ---------------------------------------------------------
def _collect_simple_overrides(state: WebGuiState) -> Dict[str, Any]:
    return collect_simple_overrides(state)

def _collect_all_overrides_for_run(state: WebGuiState) -> Dict[str, Any]:
    advanced = collect_overrides(state, SCHEMA_MAP)
    simple = _collect_simple_overrides(state)

    # Simple GUI layer intentionally wins over advanced duplicate values.
    advanced.update(simple)
    return advanced


# ---------------------------------------------------------
# Preview helpers
# ---------------------------------------------------------

def _refresh_content_mix_total_label(state: WebGuiState) -> None:
    if state.content_mix_total_label is None:
        return

    state.content_mix_total_label.text = content_mix_label(state)

    

def _wireframe_svg(
    *,
    goal: str,
    character: str,
    content_mix: str,
    text_length: str,
    table_amount: str,
    variation: str,
    width: int = 390,
    height: int = 520,
) -> str:
    margin = 34

    if text_length == "Short blocks":
        base_groups = [4, 5, 4, 5]
    elif text_length == "Long paragraphs":
        base_groups = [9, 11, 10]
    else:
        base_groups = [7, 8, 7]

    if variation == "Low":
        line_groups = base_groups[:3]
        jitter = 0
    elif variation == "High":
        line_groups = [
            max(3, x - 2) if i % 2 == 0 else x + 2
            for i, x in enumerate(base_groups + [6])
        ]
        jitter = 12
    else:
        line_groups = base_groups
        jitter = 6

    has_math = goal == "Math Document Dataset" or content_mix in {"Text + Math", "Mixed Document AI"}
    has_table = (
        table_amount in {"Some tables", "Many tables", "Table-heavy"}
        or goal == "Table-heavy Dataset"
        or content_mix in {"Text + Tables", "Mixed Document AI"}
    )
    has_figure = goal == "Full Document AI Dataset" or content_mix == "Mixed Document AI"

    noisy = character in {"Realistic Scan", "Stress Test"}
    heavy = character == "Stress Test"

    parts: List[str] = []
    parts.append(
        f'''
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
             xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="0" width="{width}" height="{height}" rx="22" fill="#111827"/>
          <rect x="22" y="22" width="{width-44}" height="{height-44}" rx="14"
                fill="#ffffff" stroke="#d1d5db" stroke-width="2"/>
          <rect x="{margin}" y="{margin}" width="{width-2*margin}" height="{height-2*margin}"
                fill="none" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="5 5"/>
        '''
    )

    y = margin + 28
    block_id = 0

    for group_lines in line_groups:
        block_h = group_lines * 13 + 20
        x0 = margin + (block_id % 2) * jitter
        block_w = width - 2 * margin - ((block_id % 3) * 22)

        parts.append(
            f'<rect x="{x0}" y="{y-12}" width="{block_w}" height="{block_h}" '
            f'rx="9" fill="none" stroke="#d1d5db" stroke-width="1"/>'
        )

        for i in range(group_lines):
            lx = x0 + 14
            ly = y + i * 13
            lw = block_w - 30 - ((i % 4) * 20)

            parts.append(
                f'<line x1="{lx}" y1="{ly}" x2="{lx+lw}" y2="{ly}" '
                f'stroke="#374151" stroke-width="2.2" '
                f'stroke-linecap="round" opacity="0.72"/>'
            )

        y += block_h + 18
        block_id += 1

        if has_math and block_id == 1:
            parts.append(
                f'<rect x="{margin+14}" y="{y}" width="{width-2*margin-28}" height="46" '
                f'rx="9" fill="#fff7ed" stroke="#f97316" stroke-width="2"/>'
            )
            parts.append(
                f'<text x="{margin+34}" y="{y+29}" font-size="14" fill="#9a3412">'
                f'equations / math mask</text>'
            )
            y += 66

        if has_table and block_id == 2:
            tx = margin + 10
            ty = y
            tw = width - 2 * margin - 20
            th = 100

            parts.append(
                f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" '
                f'rx="8" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>'
            )

            for k in range(1, 5):
                yy = ty + k * th / 5
                parts.append(
                    f'<line x1="{tx}" y1="{yy}" x2="{tx+tw}" y2="{yy}" '
                    f'stroke="#2563eb" stroke-width="1" opacity="0.55"/>'
                )

            for k in range(1, 4):
                xx = tx + k * tw / 4
                parts.append(
                    f'<line x1="{xx}" y1="{ty}" x2="{xx}" y2="{ty+th}" '
                    f'stroke="#2563eb" stroke-width="1" opacity="0.55"/>'
                )

            parts.append(
                f'<text x="{tx+14}" y="{ty+22}" font-size="12" fill="#1d4ed8">table region</text>'
            )
            y += th + 24

        if has_figure and block_id == 3:
            parts.append(
                f'<rect x="{margin+22}" y="{y}" width="{width-2*margin-44}" height="84" '
                f'rx="12" fill="#f3f4f6" stroke="#6b7280" stroke-width="2" '
                f'stroke-dasharray="7 5"/>'
            )
            parts.append(
                f'<text x="{margin+45}" y="{y+49}" font-size="14" fill="#4b5563">'
                f'figure / diagram placeholder</text>'
            )
            y += 104

    if noisy:
        parts.append(
            f'<path d="M 42 94 C 90 126, 132 82, 190 122 S 300 162, 365 122" '
            f'fill="none" stroke="#111827" stroke-width="2" opacity="0.16"/>'
        )

    if heavy:
        parts.append(
            f'<line x1="58" y1="38" x2="84" y2="{height-62}" '
            f'stroke="#111827" stroke-width="4" opacity="0.11"/>'
        )

    parts.append("</svg>")
    return "".join(parts)


def _refresh_preview(state: WebGuiState) -> None:
    if state.preview_html is None:
        return

    goal = str(state.dataset_goal_select.value or "Quick OCR Dataset")
    character = str(state.dataset_character_select.value or "Balanced")
    text_length = str(state.text_length_select.value or "Balanced blocks")

    diversity_strength = (
        str(state.diversity_strength_select.value or "Balanced diversity")
        if state.diversity_strength_select is not None
        else "Balanced diversity"
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
        state.spread_percent_input.value
        if state.spread_percent_input is not None
        else 65
    )

    gap_percent = (
        state.block_gap_percent_input.value
        if state.block_gap_percent_input is not None
        else 20
    )

    placement_search_percent = (
        state.placement_search_percent_input.value
        if state.placement_search_percent_input is not None
        else 45
    )

    content_mix_label = content_mix_preview_label(mix)
    table_amount_label = table_amount_preview_label(mix)
    density_label = density_preview_label(density_percent)

    text_p = float(mix.get("text", 0.0))
    table_p = float(mix.get("table", 0.0))
    latex_p = float(mix.get("latex", 0.0))

    if latex_p > 0 and table_p > 0:
        preview_content_mix = "Mixed Document AI"
    elif latex_p > 0:
        preview_content_mix = "Text + Math"
    elif table_p > 0:
        preview_content_mix = "Text + Tables"
    else:
        preview_content_mix = "Mostly Text"

    state.preview_html.set_content(
        _wireframe_svg(
            goal=goal,
            character=character,
            content_mix=preview_content_mix,
            text_length=text_length,
            table_amount=table_amount_label,
            variation=density_label,
        )
    )

    _refresh_content_mix_total_label(state)

    if state.simple_summary_label is not None:
        state.simple_summary_label.text = (
            f"Preset summary: {goal}, {character.lower()} visual character, "
            f"{content_mix_label}, {text_length.lower()}, "
            f"density {clamp_percent(density_percent, 50):.0f}%, "
            f"{diversity_strength.lower()}, "
            f"line spacing randomness {clamp_percent(spacing_percent, 0):.0f}%, "
            f"whitespace strategy {whitespace_strategy}, "
            f"spread {clamp_percent(spread_percent, 65):.0f}%, "
            f"block gap {clamp_percent(gap_percent, 20):.0f}%, "
            f"placement search {clamp_percent(placement_search_percent, 45):.0f}%."
        )

    _refresh_effective_yaml(state)


def _refresh_effective_yaml(state: WebGuiState) -> None:
    refresh_effective_yaml_preview(
        state,
        overrides=_collect_all_overrides_for_run(state),
    )

def _save_current_effective_yaml_debug(state: WebGuiState) -> None:
    try:
        config_path = normalize_config_path(str(state.config_path_input.value or ""))
        out_root = normalize_out_root(str(state.out_root_input.value or ""))

        overrides = _collect_all_overrides_for_run(state)

        raw_yaml_text = ""
        if state.raw_yaml_override_input is not None:
            raw_yaml_text = str(state.raw_yaml_override_input.value or "")

        yaml_text = state.orchestrator.build_effective_config_yaml_text(
            config_path=config_path,
            overrides=overrides,
            raw_yaml_override_text=raw_yaml_text,
            out_root=out_root,
            pages=_as_int(state.pages_input.value, 0),
            workers=_as_int(state.workers_input.value, 0),
            seed=_as_int(state.seed_input.value, -1),
            smoke_test=bool(state.smoke_test_input.value),
        )

        debug_dir = Path(out_root) / "_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)

        path = debug_dir / "current_gui_effective_config.yaml"
        path.write_text(yaml_text, encoding="utf-8")

        append_gui_event(
            state,
            f"Saved current GUI effective config: {path}",
            level="INFO",
        )
        safe_notify(
            state,
            f"Saved effective config: {path}",
            color="positive",
            level="INFO",
        )

    except Exception as e:
        append_gui_event(
            state,
            f"Save current effective config failed: {e!r}",
            level="ERROR",
        )
        safe_notify(
            state,
            f"Save effective config failed: {e}",
            color="negative",
            level="ERROR",
        )


# ---------------------------------------------------------
# Template preview helpers
# ---------------------------------------------------------

def _template_preview_svg(state: WebGuiState, width: int = 390, height: int = 520) -> str:
    selected_id = (
        state.selected_template_region_id
        or (state.template_region_select.value if state.template_region_select is not None else "")
    )

    page_x, page_y = 22, 22
    page_w, page_h = width - 44, height - 44

    palette = {
        "table": ("#eff6ff", "#2563eb"),
        "field": ("#fef3c7", "#d97706"),
        "text_block": ("#f3f4f6", "#6b7280"),
        "paragraph": ("#f3f4f6", "#6b7280"),
        "header": ("#ecfeff", "#0891b2"),
        "footer": ("#ecfeff", "#0891b2"),
        "math_block": ("#fff7ed", "#f97316"),
        "signature": ("#fdf2f8", "#db2777"),
        "checkbox": ("#f0fdf4", "#16a34a"),
        "checkbox_group": ("#f0fdf4", "#16a34a"),
        "figure": ("#f5f3ff", "#7c3aed"),
    }

    parts = [
        f'''
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
             xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="0" width="{width}" height="{height}" rx="22" fill="#111827"/>
          <rect x="22" y="22" width="{width-44}" height="{height-44}" rx="14"
                fill="#ffffff" stroke="#d1d5db" stroke-width="2"/>
        '''
    ]

    for row in active_template_rows(state):
        rx = page_x + float(row.get("x", 0)) * page_w
        ry = page_y + float(row.get("y", 0)) * page_h
        rw = float(row.get("w", 0.1)) * page_w
        rh = float(row.get("h", 0.1)) * page_h
        rtype = str(row.get("type", "text_block"))

        fill, stroke = palette.get(rtype, ("#f3f4f6", "#6b7280"))
        selected = str(row.get("region_id")) == str(selected_id)
        sw = 4 if selected else 2
        opacity = 0.92 if selected else 0.62
        dash = "" if rtype in {"table", "field", "header"} else ' stroke-dasharray="6 5"'

        label = str(row.get("label") or row.get("region_id") or "region")[:28]

        parts.append(
            f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" '
            f'rx="7" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'opacity="{opacity}"{dash}/>'
        )
        parts.append(
            f'<text x="{rx+7:.1f}" y="{ry+18:.1f}" '
            f'font-size="11" fill="#111827">{label}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def _refresh_template_selects(state: WebGuiState) -> None:
    names = available_template_names(state)

    if state.template_name_select is not None:
        state.template_name_select.options = {name: name for name in names}

        if names:
            if state.active_template_name not in names:
                state.active_template_name = names[0]
            state.template_name_select.value = state.active_template_name
        else:
            state.template_name_select.value = None

        _safe_update(state.template_name_select)

    rows = active_template_rows(state)
    options = {
        str(row.get("region_id")): (
            f"{row.get('region_id')} · {row.get('type')} · source={row.get('content_source', '')}"
        )
        for row in rows
    }

    if state.template_region_select is not None:
        state.template_region_select.options = options

        if options:
            if state.selected_template_region_id not in options:
                state.selected_template_region_id = next(iter(options.keys()))
            state.template_region_select.value = state.selected_template_region_id
        else:
            state.selected_template_region_id = None
            state.template_region_select.value = None

        _safe_update(state.template_region_select)


def _refresh_template_preview(state: WebGuiState) -> None:
    _refresh_template_selects(state)

    svg = _template_preview_svg(state)

    if state.template_preview_html is not None:
        state.template_preview_html.set_content(svg)

    if state.template_status_label is not None:
        active_name = state.active_template_name or "-"
        state.template_status_label.text = (
            f"Templates loaded: {len(state.template_rows)} regions. "
            f"Active template: {active_name}."
        )


def _on_template_name_selected(state: WebGuiState) -> None:
    if state.template_name_select is not None:
        state.active_template_name = str(state.template_name_select.value or "")

    rows = active_template_rows(state)
    state.selected_template_region_id = str(rows[0].get("region_id")) if rows else None

    _refresh_template_preview(state)


def _on_template_region_selected(state: WebGuiState) -> None:
    if state.template_region_select is not None:
        state.selected_template_region_id = str(state.template_region_select.value or "")

    _refresh_template_preview(state)


# ---------------------------------------------------------
# Run lifecycle
# ---------------------------------------------------------

def _set_running_ui(state: WebGuiState, is_running: bool) -> None:
    try:
        if state.start_btn is not None:
            if is_running:
                state.start_btn.disable()
            else:
                state.start_btn.enable()

        if state.stop_btn is not None:
            if is_running:
                state.stop_btn.enable()
            else:
                state.stop_btn.disable()
    except Exception:
        pass

def _start_run(state: WebGuiState) -> None:
    append_gui_event(state, "Start button clicked.", level="INFO")

    append_gui_event(
        state,
        f"Runtime cwd={Path.cwd()} project_root={_PROJECT_ROOT}",
        level="INFO",
    )

    print("[WEB] Start button clicked.", flush=True)

    with state.run_lock:
        if current_run_is_active(state):
            append_gui_event(
                state,
                "Start blocked: active run already exists.",
                level="WARN",
            )
            safe_notify(state, "A run is already active.", color="warning", level="WARN")
            return

        config_path = normalize_config_path(str(state.config_path_input.value or ""))
        out_root = normalize_out_root(str(state.out_root_input.value or ""))

        config_exists = Path(config_path).exists()

        append_gui_event(
            state,
            (
                "Resolved run paths: "
                f"config_path={config_path} exists={config_exists}, "
                f"out_root={out_root}, "
                f"cwd={Path.cwd()}"
            ),
            level="INFO",
        )

        if not config_exists:
            append_gui_event(
                state,
                f"Start blocked: config file does not exist: {config_path}",
                level="ERROR",
            )
            safe_notify(
                state,
                f"Config file not found: {config_path}",
                color="negative",
                level="ERROR",
            )
            return

        overrides = _collect_all_overrides_for_run(state)

        if not prepare_latex_or_fallback(state, overrides):
            return


        raw_yaml_text = ""
        if state.raw_yaml_override_input is not None:
            raw_yaml_text = str(state.raw_yaml_override_input.value or "")

        append_gui_event(
            state,
            (
                "Starting run with "
                f"config={config_path}, "
                f"out_root={out_root}, "
                f"pages={state.pages_input.value}, "
                f"workers={state.workers_input.value}, "
                f"seed={state.seed_input.value}, "
                f"override_keys={sorted(overrides.keys())}"
            ),
            level="INFO",
        )

        request = RunRequest(
            config_path=config_path,
            out_root=out_root,
            pages=_as_int(state.pages_input.value, 0),
            workers=_as_int(state.workers_input.value, 0),
            seed=_as_int(state.seed_input.value, -1),
            smoke_test=bool(state.smoke_test_input.value),
            overrides=overrides,
            raw_yaml_override_text=raw_yaml_text,
        )

        try:
            run_id = state.orchestrator.start(request)

            state.current_run_id = run_id

            write_active_run_state(
                run_id=run_id,
                state="running",
                out_root=out_root,
                config_path=config_path,
            )

            _set_text(state.run_id_label, run_id)
            _set_text(state.state_label, "running")
            _set_text(state.out_root_label, out_root or "-")
            _set_text(state.progress_label, "run started")

            _set_running_ui(state, True)

            append_gui_event(state, f"Run started: {run_id}", level="INFO")
            safe_notify(state, f"Run started: {run_id}", color="positive", level="INFO")

            _refresh_status(state)

        except Exception as e:
            _set_running_ui(state, False)

            append_gui_event(
                state,
                f"Run start failed: {e!r}",
                level="ERROR",
            )

            safe_notify(state, f"Run start failed: {e}", color="negative", level="ERROR")



def _stop_run(state: WebGuiState) -> None:
    append_gui_event(state, "Stop button clicked.", level="INFO")
    print("[WEB] Stop button clicked.", flush=True)

    if not state.current_run_id:
        append_gui_event(state, "Stop ignored: no active run.", level="WARN")
        safe_notify(state, "No active run to stop.", color="warning", level="WARN")
        return

    try:
        ok = state.orchestrator.cancel(state.current_run_id)

        if ok:
            append_gui_event(
                state,
                f"Run cancellation requested: {state.current_run_id}",
                level="WARN",
            )
            safe_notify(
                state,
                f"Run cancellation requested: {state.current_run_id}",
                color="warning",
                level="WARN",
            )
        else:
            append_gui_event(
                state,
                f"Run could not be cancelled: {state.current_run_id}",
                level="WARN",
            )
            safe_notify(
                state,
                "Run was not running or could not be cancelled.",
                color="warning",
                level="WARN",
            )

        # Do NOT clear active run state here.
        # _refresh_status() should clear it only when status is terminal.
        _refresh_status(state)

    except Exception as e:
        from ai1_gen.gui.web.run_state import is_unknown_run_error, reset_lost_run_state

        if is_unknown_run_error(e):
            append_gui_event(
                state,
                f"Stop failed because active run was unknown: {e!r}",
                level="ERROR",
            )
            reset_lost_run_state(state, repr(e))
            return

        append_gui_event(state, f"Stop failed: {e!r}", level="ERROR")
        safe_notify(state, f"Stop failed: {e}", color="negative", level="ERROR")


def _read_text_tail(path: Path, limit: int = 8000) -> str:
    try:
        if not path.exists() or not path.is_file():
            return ""

        text = path.read_text(encoding="utf-8", errors="replace")

        if len(text) <= limit:
            return text

        return text[-limit:]

    except Exception:
        return ""


def _read_last_error_from_status_logs(status: Any) -> str:
    candidates: list[Path] = []

    stderr_log = getattr(status, "stderr_log", None)
    if stderr_log:
        candidates.append(Path(str(stderr_log)))

    out_root = getattr(status, "out_root", None)
    if out_root:
        root = Path(str(out_root))
        candidates.extend(
            [
                root / "failed_pages.log",
                root / "errors.jsonl",
                root / "run.log",
            ]
        )

    chunks: list[str] = []

    for path in candidates:
        text = _read_text_tail(path)

        if not text:
            continue

        interesting = [
            line
            for line in text.splitlines()
            if any(
                token in line.lower()
                for token in (
                    "error",
                    "exception",
                    "traceback",
                    "failed",
                    "fatal",
                    "runtime/",
                    "abort_reason",
                )
            )
        ]

        if interesting:
            chunks.append(f"--- {path.name} ---")
            chunks.extend(interesting[-20:])

    return "\n".join(chunks).strip()


def _refresh_status(state: WebGuiState) -> None:
    refresh_live_event_log(state)

    run_id = state.current_run_id

    if not run_id:
        _set_text(state.run_id_label, "-")
        _set_text(state.state_label, "idle")
        _set_text(state.pid_label, "-")
        _set_text(state.return_code_label, "-")
        _set_text(state.out_root_label, "-")
        _set_text(state.progress_label, "no active run")
        _set_running_ui(state, False)
        return

    try:
        status = state.orchestrator.get_status(run_id)
        status_obj = status.to_dict()

        _set_text(state.run_id_label, status.run_id)
        _set_text(state.state_label, status.state)
        _set_text(state.pid_label, status.pid if status.pid is not None else "-")
        _set_text(
            state.return_code_label,
            status.return_code if status.return_code is not None else "-",
        )
        _set_text(state.out_root_label, status.out_root or "-")

        if status.progress is not None:
            _set_text(state.progress_label, status.progress.message or status.state)
        else:
            _set_text(state.progress_label, status.state)

        _set_value(state.status_json, _json_dumps(status_obj))

        if status.stdout_log:
            _set_value(state.stdout_log, tail_text(status.stdout_log, 16000))

        if status.stderr_log:
            _set_value(state.stderr_log, tail_text(status.stderr_log, 16000))

        if str(status.state) in {"failed", "error"}:
            last_error = _read_last_error_from_status_logs(status)

            if last_error:
                _set_value(state.stderr_log, last_error)
                append_gui_event(
                    state,
                    f"Run failed with visible error details:\n{last_error}",
                    level="ERROR",
                )
            else:
                append_gui_event(
                    state,
                    "Run failed but no detailed error log was found.",
                    level="ERROR",
                )

        try:
            summary = state.orchestrator.get_summary(run_id)
            _set_value(state.summary_json, _json_dumps(summary.to_dict()))
        except Exception as e:
            append_gui_event(
                state,
                f"Summary refresh skipped or failed: {e!r}",
                level="WARN",
            )

        if status.state in TERMINAL_RUN_STATES:
            append_gui_event(
                state,
                (
                    f"Run reached terminal state: {status.state}, "
                    f"return_code={status.return_code}"
                ),
                level="INFO" if status.state == "done" else "WARN",
            )

            clear_active_run_state()
            _set_running_ui(state, False)
        else:
            _set_running_ui(state, True)

    except Exception as e:
        append_gui_event(
            state,
            f"Status refresh failed: {e!r}",
            level="ERROR",
        )
        safe_notify(state, f"Status refresh failed: {e}", color="negative", level="ERROR")

def _save_current_effective_yaml_debug(state: WebGuiState) -> None:
    try:
        config_path = normalize_config_path(str(state.config_path_input.value or ""))
        out_root = normalize_out_root(str(state.out_root_input.value or ""))

        overrides = _collect_all_overrides_for_run(state)

        raw_yaml_text = ""
        if state.raw_yaml_override_input is not None:
            raw_yaml_text = str(state.raw_yaml_override_input.value or "")

        yaml_text = state.orchestrator.build_effective_config_yaml_text(
            config_path=config_path,
            overrides=overrides,
            raw_yaml_override_text=raw_yaml_text,
            out_root=out_root,
            pages=_as_int(state.pages_input.value, 0),
            workers=_as_int(state.workers_input.value, 0),
            seed=_as_int(state.seed_input.value, -1),
            smoke_test=bool(state.smoke_test_input.value),
        )

        debug_dir = Path(out_root) / "_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)

        path = debug_dir / "current_gui_effective_config.yaml"
        path.write_text(yaml_text, encoding="utf-8")

        append_gui_event(
            state,
            f"Saved current GUI effective config: {path}",
            level="INFO",
        )
        safe_notify(
            state,
            f"Saved effective config: {path}",
            color="positive",
            level="INFO",
        )

    except Exception as e:
        append_gui_event(
            state,
            f"Save current effective config failed: {e!r}",
            level="ERROR",
        )
        safe_notify(
            state,
            f"Save effective config failed: {e}",
            color="negative",
            level="ERROR",
        )



def _restore_run_on_startup(state: WebGuiState) -> None:
    try:
        restored = restore_active_run_from_disk(state)

        if restored:
            _refresh_status(state)
    except Exception as e:
        append_gui_event(state, f"Run restore failed: {e}", level="ERROR")


# ---------------------------------------------------------
# Advanced schema UI
# ---------------------------------------------------------

def _make_schema_widget(state: WebGuiState, field: Dict[str, Any]) -> Any:
    key = field.get("key", "")
    label = field.get("label", key)
    field_type = field.get("field_type", "str")
    default = field.get("default")
    help_text = field.get("help_text", "")

    if field_type == "bool":
        widget = ui.switch(label, value=bool(default))

    elif field_type == "enum":
        choices = field.get("choices", []) or []
        widget = ui.select(
            options={str(x): str(x) for x in choices},
            label=label,
            value=str(default) if default is not None else (str(choices[0]) if choices else None),
        ).classes("w-full")

    elif field_type == "int":
        widget = ui.number(
            label=label,
            value=int(default if default is not None else 0),
            min=field.get("minimum"),
            max=field.get("maximum"),
            step=field.get("step") or 1,
        ).classes("w-full")

    elif field_type == "float":
        widget = ui.number(
            label=label,
            value=float(default if default is not None else 0.0),
            min=field.get("minimum"),
            max=field.get("maximum"),
            step=field.get("step") or 0.1,
        ).classes("w-full")

    elif field_type in {"json", "color_rgb"}:
        widget = ui.textarea(
            label=label,
            value=json.dumps(default if default is not None else {}, ensure_ascii=False),
        ).classes("w-full").props("autogrow")

    else:
        widget = ui.input(
            label=label,
            value="" if default is None else str(default),
        ).classes("w-full")

    if help_text:
        widget.tooltip(str(help_text))

    widget.on("update:model-value", lambda *_: _refresh_effective_yaml(state))
    state.field_widgets[key] = widget

    return widget


def _build_advanced_schema_panel(state: WebGuiState) -> None:
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for field in SCHEMA_MAP.values():
        if field.get("visibility") != "advanced":
            continue

        grouped.setdefault(str(field.get("group", "Advanced")), []).append(field)

    if not grouped:
        ui.label("No advanced schema fields found.").classes("text-sm text-gray-500")
        return

    for group, fields in sorted(grouped.items()):
        with ui.expansion(group, icon="tune").classes("w-full"):
            with ui.grid(columns=2).classes("w-full gap-3"):
                for field in fields:
                    _make_schema_widget(state, field)


# ---------------------------------------------------------
# App UI
# ---------------------------------------------------------

def _install_page_style() -> None:
    ui.add_head_html(
        """
        <style>
          body {
            background: #f3f4f6;
          }

          .ai-page {
            width: 100%;
            max-width: 1520px;
            margin: 0 auto;
            padding: 18px;
          }

          .ai-card {
            border-radius: 18px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
            border: 1px solid #e5e7eb;
            background: white;
          }

          .ai-muted {
            color: #6b7280;
            font-size: 13px;
          }

          .ai-section-title {
            font-size: 18px;
            font-weight: 700;
            color: #111827;
            margin-bottom: 4px;
          }

          .ai-section-subtitle {
            color: #6b7280;
            font-size: 13px;
            margin-bottom: 12px;
          }

          .ai-status-pill {
            border-radius: 999px;
            padding: 4px 10px;
            background: #eef2ff;
            color: #3730a3;
            font-size: 12px;
            font-weight: 600;
          }
        </style>
        """
    )


def _section_header(title: str, subtitle: str = "") -> None:
    ui.label(title).classes("ai-section-title")

    if subtitle:
        ui.label(subtitle).classes("ai-section-subtitle")


def _build_top_run_bar(state: WebGuiState) -> None:
    with ui.card().classes("ai-card w-full"):
        with ui.row().classes("w-full items-center justify-between gap-3"):
            with ui.column().classes("gap-0"):
                ui.label("AI1 Gen").classes("text-2xl font-bold text-gray-900")
                ui.label("Synthetic Document AI dataset generator").classes("text-sm text-gray-500")

            with ui.row().classes("items-center gap-2"):
                state.start_btn = ui.button(
                    "Start",
                    icon="play_arrow",
                    color="positive",
                    on_click=lambda: _start_run(state),
                )

                state.stop_btn = ui.button(
                    "Stop",
                    icon="stop",
                    color="negative",
                    on_click=lambda: _stop_run(state),
                )
                state.stop_btn.disable()

                ui.button(
                    "Save effective config",
                    icon="save",
                    on_click=lambda: _save_current_effective_yaml_debug(state),
                )

                ui.button(
                    "Refresh",
                    icon="refresh",
                    on_click=lambda: _refresh_status(state),
                )

                ui.button(
                    "Open output",
                    icon="folder_open",
                    on_click=lambda: open_path(str(state.out_root_label.text))
                    if state.out_root_label is not None and str(state.out_root_label.text) not in {"", "-"}
                    else ui.notify("No output path yet.", color="warning"),
                )

        ui.separator()

        with ui.grid(columns=4).classes("w-full gap-3"):
            state.config_path_input = ui.input(
                "Config path",
                value=str(DEFAULT_CONFIG),
            ).classes("w-full")

            state.out_root_input = ui.input(
                "Output root",
                value="out/web_gui_run",
            ).classes("w-full")

            state.pages_input = ui.number(
                "Pages",
                value=20,
                min=1,
                step=1,
            ).classes("w-full")

            state.workers_input = ui.number(
                "Workers",
                value=2,
                min=1,
                step=1,
            ).classes("w-full")

        with ui.row().classes("w-full items-center gap-4"):
            state.seed_input = ui.number(
                "Seed",
                value=1337,
                step=1,
            ).classes("w-48")

            state.smoke_test_input = ui.switch("Smoke test", value=False)

            ui.space()

            ui.label("Status is shown in the Run Monitor tab").classes("text-xs text-gray-500")

        for widget in (
            state.config_path_input,
            state.out_root_input,
            state.pages_input,
            state.workers_input,
            state.seed_input,
            state.smoke_test_input,
        ):
            widget.on("update:model-value", lambda *_: _refresh_effective_yaml(state))



def _build_dataset_controls_card(state: WebGuiState) -> None:
    with ui.card().classes("ai-card w-full"):
        _section_header(
            "1. Hazır ayarlar",
            "Dataset hedefini, görsel karakteri ve içerik türünü seç. Detaylar gelişmiş ayarlarda.",
        )

        with ui.grid(columns=2).classes("w-full gap-3"):
            state.dataset_goal_select = ui.select(
                options=list(DATASET_GOAL_PRESETS.keys()),
                value="Quick OCR Dataset",
                label="Hazır ayar",
            ).classes("w-full")

            state.dataset_character_select = ui.select(
                options=list(DATASET_CHARACTER_PRESETS.keys()),
                value="Balanced",
                label="Görsel karakter",
            ).classes("w-full")

            state.content_mix_preset_select = ui.select(
                options=list(CONTENT_MIX_PRESETS.keys()),
                value="Karışık belge",
                label="İçerik türü",
            ).classes("w-full")

        state.simple_summary_label = ui.label("").classes("text-sm text-gray-700")

        for widget in (
            state.dataset_goal_select,
            state.dataset_character_select,
            state.content_mix_preset_select,
        ):
            widget.on(
                "update:model-value",
                lambda *_: (
                    sync_custom_mix_visibility(state),
                    _refresh_preview(state),
                ),
            )

            
def _build_content_mix_card(state: WebGuiState) -> None:
    with ui.card().classes("ai-card w-full"):
        _section_header(
            "2. Özel içerik yüzdeleri",
            "Sadece içerik türü 'Özel' seçildiğinde kullanılır. Toplam otomatik 100'e normalize edilir.",
        )

        with ui.column().classes("w-full gap-3") as panel:
            state.custom_content_mix_panel = panel

            with ui.grid(columns=3).classes("w-full gap-3"):
                state.text_mix_input = ui.number(
                    "Text (%)",
                    value=60,
                    min=0,
                    max=100,
                    step=1,
                ).classes("w-full")

                state.table_mix_input = ui.number(
                    "Table (%)",
                    value=25,
                    min=0,
                    max=100,
                    step=1,
                ).classes("w-full")

                state.latex_mix_input = ui.number(
                    "LaTeX (%)",
                    value=15,
                    min=0,
                    max=100,
                    step=1,
                ).classes("w-full")

            state.content_mix_total_label = ui.label("").classes("text-sm text-gray-600")

        for widget in (
            state.text_mix_input,
            state.table_mix_input,
            state.latex_mix_input,
        ):
            widget.on("update:model-value", lambda *_: _refresh_preview(state))

        sync_custom_mix_visibility(state)


def _build_layout_behavior_card(state: WebGuiState) -> None:
    with ui.card().classes("ai-card w-full"):
        _section_header(
            "Gelişmiş üretim ayarları",
            "Density, whitespace, placement ve LaTeX renderer gibi teknik ayarlar.",
        )

        with ui.expansion("Belge çeşitliliği", icon="dashboard_customize").classes("w-full"):
            with ui.grid(columns=2).classes("w-full gap-3"):
                state.document_template_select = ui.select(
                    options=list(DOCUMENT_TEMPLATE_PRESETS.keys()),
                    value="Generic random document",
                    label="Document template",
                ).classes("w-full")

                state.diversity_strength_select = ui.select(
                    options=list(DIVERSITY_STRENGTH_PRESETS.keys()),
                    value="Balanced diversity",
                    label="Diversity strength",
                ).classes("w-full")

                state.text_length_select = ui.select(
                    options=list(TEXT_LENGTH_PRESETS.keys()),
                    value="Balanced blocks",
                    label="Text length",
                ).classes("w-full")

                state.content_source_mode_select = ui.select(
                    options={
                        "content_bank": "Content bank",
                        "random_chars": "Random characters",
                    },
                    value="content_bank",
                    label="Content source",
                ).classes("w-full")

        with ui.expansion("Yerleşim ve yoğunluk", icon="view_quilt").classes("w-full"):
            with ui.grid(columns=2).classes("w-full gap-3"):
                state.density_percent_input = ui.number(
                    "Density (%)",
                    value=50,
                    min=0,
                    max=100,
                    step=1,
                ).classes("w-full")

                state.line_gap_tolerance_input = ui.number(
                    "Line spacing randomness (%)",
                    value=0,
                    min=0,
                    max=100,
                    step=1,
                ).classes("w-full")

                state.whitespace_strategy_select = ui.select(
                    options={
                        "balanced": "Balanced",
                        "spread": "Spread",
                        "compact": "Compact",
                    },
                    value="balanced",
                    label="Whitespace strategy",
                ).classes("w-full")

                state.spread_percent_input = ui.number(
                    "Spread (%)",
                    value=65,
                    min=0,
                    max=100,
                    step=1,
                ).classes("w-full")

                state.block_gap_percent_input = ui.number(
                    "Block gap (%)",
                    value=20,
                    min=0,
                    max=100,
                    step=1,
                ).classes("w-full")

                state.placement_search_percent_input = ui.number(
                    "Placement search (%)",
                    value=45,
                    min=0,
                    max=100,
                    step=1,
                ).classes("w-full")

        with ui.expansion("LaTeX renderer", icon="functions").classes("w-full"):
            state.latex_render_enable_switch = ui.switch(
                "LaTeX render etkin",
                value=True,
            )

            state.latex_http_base_url_input = ui.input(
                "Renderer URL",
                value="http://127.0.0.1:8080",
            ).classes("w-full")

            state.latex_missing_behavior_select = ui.select(
                options=LATEX_MISSING_BEHAVIORS,
                value="LaTeX'i kapat ve devam et",
                label="Renderer hazır değilse",
            ).classes("w-full")

            state.latex_status_label = ui.label(
                "LaTeX opsiyonel. Renderer yoksa varsayılan olarak kapatılıp devam edilir."
            ).classes("text-sm text-gray-500")

        for widget in (
            state.document_template_select,
            state.diversity_strength_select,
            state.text_length_select,
            state.content_source_mode_select,
            state.density_percent_input,
            state.line_gap_tolerance_input,
            state.whitespace_strategy_select,
            state.spread_percent_input,
            state.block_gap_percent_input,
            state.placement_search_percent_input,
            state.latex_render_enable_switch,
            state.latex_http_base_url_input,
            state.latex_missing_behavior_select,
        ):
            widget.on("update:model-value", lambda *_: _refresh_preview(state))



def _build_preview_card(state: WebGuiState) -> None:
    with ui.card().classes("ai-card w-full"):
        _section_header(
            "Live preview",
            "Approximate wireframe only. It shows the expected document structure, not final generated pixels.",
        )

        with ui.row().classes("w-full justify-center"):
            state.preview_html = ui.html("").classes("w-full")

        state.preview_caption = ui.label(
            "Use this preview to check whether the dataset shape feels right before running."
        ).classes("text-sm text-gray-500")


def _build_create_dataset_tab(state: WebGuiState) -> None:
    with ui.row().classes("w-full gap-4 items-start"):
        with ui.column().classes("w-full lg:w-7/12 gap-4"):
            _build_dataset_controls_card(state)
            _build_content_mix_card(state)
            _build_layout_behavior_card(state)

        with ui.column().classes("w-full lg:w-5/12 gap-4 sticky top-4"):
            _build_preview_card(state)


def _build_content_card(state: WebGuiState) -> None:
    with ui.card().classes("ai-card w-full"):
        _section_header(
            "Content CSVs",
            "Manage words/sentences content files used by the content bank.",
        )

        with ui.row().classes("gap-2"):
            ui.button(
                "Reset sample CSVs",
                icon="restart_alt",
                color="warning",
                on_click=reset_content_csvs,
            )

            ui.button(
                "Ensure content bank",
                icon="check",
                color="positive",
                on_click=lambda: ensure_custom_content_csvs(state),
            )

        ui.separator()

        with ui.grid(columns=2).classes("w-full gap-3"):
            ui.upload(
                label="Upload words.csv",
                auto_upload=True,
                on_upload=lambda e: save_uploaded_content_csv(state, e, "words.csv"),
            ).props("accept=.csv").classes("w-full")

            ui.upload(
                label="Upload sentences.csv",
                auto_upload=True,
                on_upload=lambda e: save_uploaded_content_csv(state, e, "sentences.csv"),
            ).props("accept=.csv").classes("w-full")


def _build_template_card(state: WebGuiState) -> None:
    with ui.card().classes("ai-card w-full"):
        _section_header(
            "Template CSV",
            "Upload or export document region templates. This is for fixed-form layouts like invoices or checklists.",
        )

        state.template_status_label = ui.label("No template loaded.").classes("text-sm text-gray-600")

        with ui.row().classes("gap-2 items-center"):
            ui.upload(
                label="Upload template CSV",
                auto_upload=True,
                on_upload=lambda e: handle_template_csv_upload(
                    state,
                    e,
                    on_loaded=lambda: _refresh_template_preview(state),
                ),
            ).props("accept=.csv").classes("max-w-full")

            ui.button(
                "Export example",
                icon="download",
                on_click=lambda: export_template_csv_example(state),
            )

            ui.button(
                "Open CSV",
                icon="folder_open",
                on_click=lambda: open_template_csv(state),
            )

        ui.separator()

        with ui.grid(columns=3).classes("w-full gap-3"):
            state.template_name_select = ui.select(
                options={},
                label="Template",
            ).classes("w-full")

            state.template_region_select = ui.select(
                options={},
                label="Region",
            ).classes("w-full")

            state.template_region_type_select = ui.select(
                options=TEMPLATE_REGION_TYPES,
                value="text_block",
                label="Region type",
            ).classes("w-full")

        state.template_name_select.on("update:model-value", lambda *_: _on_template_name_selected(state))
        state.template_region_select.on("update:model-value", lambda *_: _on_template_region_selected(state))

        with ui.row().classes("w-full justify-center"):
            state.template_preview_html = ui.html("").classes("w-full")


def _build_templates_content_tab(state: WebGuiState) -> None:
    with ui.row().classes("w-full gap-4 items-start"):
        with ui.column().classes("w-full lg:w-5/12 gap-4"):
            _build_content_card(state)

        with ui.column().classes("w-full lg:w-7/12 gap-4"):
            _build_template_card(state)


def _build_run_status_overview(state: WebGuiState) -> None:
    with ui.card().classes("ai-card w-full"):
        _section_header(
            "Run monitor",
            "Track the active generation process, output path and latest progress.",
        )

        with ui.grid(columns=5).classes("w-full gap-3"):
            with ui.column().classes("gap-0"):
                ui.label("State").classes("text-xs text-gray-500")
                state.state_label = ui.label("idle").classes("font-mono")

            with ui.column().classes("gap-0"):
                ui.label("Run ID").classes("text-xs text-gray-500")
                state.run_id_label = ui.label("-").classes("font-mono text-xs")

            with ui.column().classes("gap-0"):
                ui.label("PID").classes("text-xs text-gray-500")
                state.pid_label = ui.label("-").classes("font-mono")

            with ui.column().classes("gap-0"):
                ui.label("Return code").classes("text-xs text-gray-500")
                state.return_code_label = ui.label("-").classes("font-mono")

            with ui.column().classes("gap-0"):
                ui.label("Progress").classes("text-xs text-gray-500")
                state.progress_label = ui.label("no active run").classes("font-mono")

        ui.separator()

        ui.label("Output root").classes("text-xs text-gray-500")
        state.out_root_label = ui.label("-").classes("font-mono text-sm")


def _build_logs_tabs(state: WebGuiState) -> None:
    with ui.card().classes("ai-card w-full"):
        with ui.tabs().classes("w-full") as tabs:
            tab_status = ui.tab("Status JSON")
            tab_summary = ui.tab("Summary JSON")
            tab_stdout = ui.tab("stdout")
            tab_stderr = ui.tab("stderr")
            tab_events = ui.tab("GUI events")

        with ui.tab_panels(tabs, value=tab_status).classes("w-full"):
            with ui.tab_panel(tab_status):
                state.status_json = ui.textarea(value="{}").classes("w-full").props("readonly autogrow")
            with ui.tab_panel(tab_summary):
                state.summary_json = ui.textarea(value="{}").classes("w-full").props("readonly autogrow")
            with ui.tab_panel(tab_stdout):
                state.stdout_log = ui.textarea(value="").classes("w-full").props("readonly autogrow")
            with ui.tab_panel(tab_stderr):
                state.stderr_log = ui.textarea(value="").classes("w-full").props("readonly autogrow")
            with ui.tab_panel(tab_events):
                state.live_event_status_label = ui.label("-").classes("text-sm text-gray-500")
                state.live_event_log = ui.textarea(value="").classes("w-full").props("readonly autogrow")


def _build_run_monitor_tab(state: WebGuiState) -> None:
    _build_run_status_overview(state)
    _build_logs_tabs(state)


def _build_effective_yaml_card(state: WebGuiState) -> None:
    with ui.card().classes("ai-card w-full"):
        _section_header(
            "Effective YAML",
            "Generated final config preview after presets, advanced fields and raw YAML override.",
        )

        state.user_yaml_path_label = ui.label("-").classes("text-sm text-gray-500")

        with ui.expansion("Raw YAML override", icon="edit_note").classes("w-full"):
            state.raw_yaml_override_input = ui.textarea(
                label="Optional raw YAML override",
                value="",
            ).classes("w-full").props("autogrow")
            state.raw_yaml_override_input.on("update:model-value", lambda *_: _refresh_effective_yaml(state))

        state.effective_yaml_preview = ui.textarea(value="").classes("w-full").props("readonly autogrow")


def _build_advanced_schema_card(state: WebGuiState) -> None:
    with ui.card().classes("ai-card w-full"):
        _section_header(
            "Advanced schema fields",
            "Use this only when the simple controls are not enough.",
        )

        with ui.row().classes("gap-2 mb-2"):
            ui.button(
                "Reload baseline/user config",
                icon="refresh",
                on_click=lambda: (
                    load_baseline_and_user_config(state, SCHEMA_MAP),
                    _refresh_effective_yaml(state),
                    ui.notify("Baseline/user config loaded", color="positive"),
                ),
            )

        _build_advanced_schema_panel(state)


def _build_advanced_tab(state: WebGuiState) -> None:
    with ui.row().classes("w-full gap-4 items-start"):
        with ui.column().classes("w-full lg:w-6/12 gap-4"):
            _build_effective_yaml_card(state)

        with ui.column().classes("w-full lg:w-6/12 gap-4"):
            _build_advanced_schema_card(state)


def build_ui() -> None:
    state = STATE

    _install_page_style()
    ui.page_title("AI1 Gen Web GUI")

    with ui.header().classes("items-center justify-between"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("description").classes("text-2xl")
            ui.label("AI1 Gen").classes("text-xl font-bold")
            ui.label("Dataset Builder").classes("text-sm opacity-70")

        ui.label("Web GUI").classes("text-sm opacity-70")

    with ui.column().classes("ai-page gap-4"):
        _build_top_run_bar(state)

        with ui.tabs().classes("w-full") as main_tabs:
            tab_create = ui.tab("Create Dataset", icon="dashboard_customize")
            tab_templates = ui.tab("Templates & Content", icon="table_chart")
            tab_monitor = ui.tab("Run Monitor", icon="monitor_heart")
            tab_advanced = ui.tab("Advanced", icon="tune")

        with ui.tab_panels(main_tabs, value=tab_create).classes("w-full"):
            with ui.tab_panel(tab_create):
                _build_create_dataset_tab(state)

            with ui.tab_panel(tab_templates):
                _build_templates_content_tab(state)

            with ui.tab_panel(tab_monitor):
                _build_run_monitor_tab(state)

            with ui.tab_panel(tab_advanced):
                _build_advanced_tab(state)

    ui.timer(2.0, lambda: _refresh_status(state))
    ui.timer(3.0, lambda: refresh_live_event_log(state))

    _restore_run_on_startup(state)

    try:
        load_baseline_and_user_config(state, SCHEMA_MAP)
    except Exception as e:
        append_gui_event(state, f"Initial config load failed: {e}", level="WARN")

    _refresh_preview(state)
    _refresh_effective_yaml(state)



def main() -> None:
    build_ui()
    ui.run(
        title="AI1 Gen Web GUI",
        host="127.0.0.1",
        port=8000,
        reload=False,
        show=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()