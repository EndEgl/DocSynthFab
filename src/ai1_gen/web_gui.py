# src/ai1_gen/web_gui.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - nicegui>=2.0,<3.0
# - PyYAML>=6.0,<7.0

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional
import csv
import io

import yaml
from nicegui import ui

# Dosya doğrudan çalıştırılırsa package root'u sys.path'e ekle
_THIS_FILE = Path(__file__).resolve()
_PKG_DIR = _THIS_FILE.parent              # .../ai1_gen/src/ai1_gen
_SRC_ROOT = _THIS_FILE.parents[1]         # .../ai1_gen/src
_PROJECT_ROOT = _THIS_FILE.parents[2]     # .../ai1_gen

if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

_DEFAULT_CONFIG = _PROJECT_ROOT / "configs" / "default.yaml"

from ai1_gen.orchestrator import RunOrchestrator, RunRequest
from ai1_gen.orchestrator.result_store import tail_text


orchestrator = RunOrchestrator()
current_run_id: Optional[str] = None
field_widgets: Dict[str, Any] = {}
run_lock = threading.Lock()

raw_yaml_override_input = None
effective_yaml_preview = None
user_yaml_path_label = None

config_path_input = None
out_root_input = None
pages_input = None
workers_input = None
seed_input = None
smoke_test_input = None

start_btn = None
stop_btn = None

run_id_label = None
state_label = None
pid_label = None
return_code_label = None
out_root_label = None
progress_label = None

summary_json = None
status_json = None
stdout_log = None
stderr_log = None
csv_upload_widget = None

baseline_overrides: Dict[str, Any] = {}
_csv_loading_mode = False



def _resolve_user_path(value: str, *, base_dir: Path = _PROJECT_ROOT, allow_empty: bool = False) -> str:
    txt = str(value or "").strip()
    if not txt:
        return "" if allow_empty else str(base_dir.resolve())

    p = Path(txt)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    else:
        p = p.resolve()
    return str(p)


def _normalize_config_path(value: str) -> str:
    return _resolve_user_path(value, base_dir=_PROJECT_ROOT, allow_empty=False)


def _normalize_out_root(value: str) -> str:
    return _resolve_user_path(value, base_dir=_PROJECT_ROOT, allow_empty=True)


def _safe_json_loads(text: str, fallback: Any = None) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return fallback


def _schema_map() -> Dict[str, Dict[str, Any]]:
    return {f["key"]: f for f in orchestrator.get_schema_for_ui()}


SCHEMA_MAP = _schema_map()


def _read_widget_value(field_key: str, widget: Any) -> Any:
    field = SCHEMA_MAP.get(field_key, {})
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
        return _safe_json_loads(txt, txt)
    return txt


def _collect_overrides() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, widget in field_widgets.items():
        value = _read_widget_value(key, widget)
        field = SCHEMA_MAP.get(key, {})
        field_type = field.get("field_type", "str")

        if field_type == "json" and value == {}:
            continue
        if field_type == "path" and str(value or "").strip() == "":
            continue
        if field_type == "str" and str(value or "").strip() == "":
            continue

        out[key] = value
    return out


def _nested_from_flat_overrides(flat: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in flat.items():
        cur = out
        parts = key.split(".")
        for part in parts[:-1]:
            nxt = cur.get(part)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[part] = nxt
            cur = nxt
        cur[parts[-1]] = value
    return out


def _lookup_nested_value(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _load_form_from_override_map(override_map: Dict[str, Any]) -> None:
    for key, widget in field_widgets.items():
        value = override_map.get(key, SCHEMA_MAP.get(key, {}).get("default"))

        try:
            field = SCHEMA_MAP.get(key, {})
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


def _build_current_effective_yaml() -> str:
    config_path = _normalize_config_path(str(config_path_input.value or ""))
    out_root = _normalize_out_root(str(out_root_input.value or ""))

    raw_yaml_text = ""
    if raw_yaml_override_input is not None:
        raw_yaml_text = str(raw_yaml_override_input.value or "")

    return orchestrator.build_effective_config_yaml_text(
        config_path=config_path,
        overrides=_collect_overrides(),
        raw_yaml_override_text=raw_yaml_text,
        out_root=out_root,
        pages=int(pages_input.value or 0),
        workers=int(workers_input.value or 0),
        seed=int(seed_input.value or -1),
        smoke_test=bool(smoke_test_input.value),
    )


def _refresh_effective_yaml_preview() -> None:
    if effective_yaml_preview is None:
        return
    try:
        effective_yaml_preview.value = _build_current_effective_yaml()
    except Exception as e:
        effective_yaml_preview.value = f"# preview error\n{e}"


def _load_baseline_and_user_config() -> None:
    global baseline_overrides

    config_path = _normalize_config_path(str(config_path_input.value or ""))

    baseline_overrides = orchestrator.build_baseline_override_map(
        config_path,
        visibility="advanced",
    )

    merged_cfg = orchestrator.build_config_with_user_override(
        config_path=config_path,
        overrides=None,
        raw_yaml_override_text=None,
    )

    current_map = dict(baseline_overrides)
    for key in current_map.keys():
        current_map[key] = _lookup_nested_value(
            merged_cfg,
            key,
            baseline_overrides.get(key),
        )

    _load_form_from_override_map(current_map)

    if user_yaml_path_label is not None:
        user_yaml_path_label.text = str(orchestrator.get_user_config_path(config_path))

    if raw_yaml_override_input is not None:
        raw_yaml_override_input.value = ""

    _refresh_effective_yaml_preview()


def _open_path(path: str) -> None:
    p = str(Path(path))
    if os.name == "nt":
        os.startfile(p)  # type: ignore[attr-defined]
    else:
        import subprocess
        if os.uname().sysname == "Darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])


def _on_any_field_change(*_: Any) -> None:
    _refresh_effective_yaml_preview()

def _on_config_path_change(e: Any) -> None:
    if _csv_loading_mode:
        return
    _load_baseline_and_user_config()

def _make_field(field: Dict[str, Any], container) -> None:
    key = field["key"]
    label = field.get("label", key)
    help_text = field.get("help_text", "")
    field_type = field.get("field_type", "str")
    default = field.get("default", None)
    choices = field.get("choices", []) or []

    with container:
        if field_type == "bool":
            w = ui.switch(label, value=bool(default))
            if help_text:
                w.tooltip(help_text)

        elif field_type == "enum":
            opts = {str(ch): ch for ch in choices}
            w = ui.select(
                options=opts,
                value=default if default in choices else (choices[0] if choices else None),
                label=label,
            )
            if help_text:
                w.tooltip(help_text)

        elif field_type == "int":
            w = ui.number(
                label=label,
                value=default if default is not None else 0,
                step=1,
            )
            if field.get("minimum") is not None:
                w.props(f'min={int(field["minimum"])}')
            if field.get("maximum") is not None:
                w.props(f'max={int(field["maximum"])}')
            if help_text:
                w.tooltip(help_text)

        elif field_type == "float":
            step = field.get("step", 0.01) or 0.01
            w = ui.number(
                label=label,
                value=default if default is not None else 0.0,
                step=step,
                format="%.6f",
            )
            if field.get("minimum") is not None:
                w.props(f'min={float(field["minimum"])}')
            if field.get("maximum") is not None:
                w.props(f'max={float(field["maximum"])}')
            if help_text:
                w.tooltip(help_text)

        else:
            initial = ""
            if default is not None:
                if field_type in {"json", "color_rgb"}:
                    initial = json.dumps(default, ensure_ascii=False)
                else:
                    initial = str(default)
            if field_type == "json":
                w = ui.textarea(label=label, value=initial).classes('w-full').props('rows=4')
            else:
                w = ui.input(label=label, value=initial)
            if help_text:
                w.tooltip(help_text)

        try:
            w.on_value_change(_on_any_field_change)
        except Exception:
            pass

        field_widgets[key] = w


def _build_grouped_fields(schema: list[Dict[str, Any]], title_prefix: str = "") -> None:
    groups: Dict[str, list[Dict[str, Any]]] = {}
    for field in schema:
        groups.setdefault(field.get("group", "Other"), []).append(field)

    for group_name, fields in groups.items():
        with ui.expansion(f'{title_prefix}{group_name}', icon='tune', value=False).classes('w-full'):
            with ui.column().classes('w-full gap-2'):
                for field in fields:
                    _make_field(field, ui.row().classes('w-full'))


def _status_to_text(status_obj) -> str:
    if status_obj is None:
        return "-"
    return json.dumps(status_obj.to_dict(), ensure_ascii=False, indent=2)


def _summary_to_text(summary_obj) -> str:
    if summary_obj is None:
        return "-"
    return json.dumps(summary_obj.to_dict(), ensure_ascii=False, indent=2)


def _refresh_status_panels() -> None:
    global current_run_id

    if not current_run_id:
        state_label.text = 'idle'
        run_id_label.text = '-'
        return

    try:
        status = orchestrator.get_status(current_run_id)
        summary = orchestrator.get_summary(current_run_id)

        run_id_label.text = current_run_id
        state_label.text = status.state
        pid_label.text = str(status.pid) if status.pid is not None else '-'
        return_code_label.text = str(status.return_code) if status.return_code is not None else '-'
        out_root_label.text = status.out_root or '-'
        progress_label.text = status.progress.state if status.progress else '-'

        status_json.value = _status_to_text(status)
        summary_json.value = _summary_to_text(summary)

        if status.stdout_log:
            stdout_log.value = tail_text(status.stdout_log, 12000)
        if status.stderr_log:
            stderr_log.value = tail_text(status.stderr_log, 12000)

        if status.state in {'done', 'failed', 'cancelled'}:
            start_btn.enable()
            stop_btn.disable()

    except Exception as e:
        ui.notify(f'Status refresh error: {e}', color='negative')


def _save_advanced_to_user_yaml() -> None:
    try:
        config_path = _normalize_config_path(str(config_path_input.value or ""))

        nested = _nested_from_flat_overrides(_collect_overrides())

        raw_yaml_text = ""
        if raw_yaml_override_input is not None:
            raw_yaml_text = str(raw_yaml_override_input.value or "").strip()

        if raw_yaml_text:
            raw_dict = orchestrator.parse_raw_yaml_override(raw_yaml_text)
            nested = orchestrator.merge_raw_yaml_override(nested, yaml.safe_dump(raw_dict, sort_keys=False, allow_unicode=True))

        saved_path = orchestrator.save_user_override_dict(config_path, nested)

        if user_yaml_path_label is not None:
            user_yaml_path_label.text = str(saved_path)

        _refresh_effective_yaml_preview()
        ui.notify(f"Saved: {saved_path}", color="positive")
    except Exception as e:
        ui.notify(f"Save failed: {e}", color="negative")


def _reset_advanced_to_baseline() -> None:
    global baseline_overrides
    try:
        config_path = _normalize_config_path(str(config_path_input.value or ""))
        orchestrator.reset_user_override_dict(config_path)

        baseline_overrides = orchestrator.build_baseline_override_map(
            config_path,
            visibility="advanced",
        )
        _load_form_from_override_map(baseline_overrides)

        if raw_yaml_override_input is not None:
            raw_yaml_override_input.value = ""

        if user_yaml_path_label is not None:
            user_yaml_path_label.text = str(orchestrator.get_user_config_path(config_path))

        _refresh_effective_yaml_preview()
        ui.notify("Advanced settings reset to baseline", color="warning")
    except Exception as e:
        ui.notify(f"Reset failed: {e}", color="negative")


def _reload_from_yaml_files() -> None:
    try:
        _load_baseline_and_user_config()
        ui.notify("Reloaded from default.yaml + default.user.yaml", color="positive")
    except Exception as e:
        ui.notify(f"Reload failed: {e}", color="negative")


def _start_run() -> None:
    global current_run_id

    with run_lock:
        try:
            config_path = _normalize_config_path(str(config_path_input.value or ""))
            out_root = _normalize_out_root(str(out_root_input.value or ""))

            config_path_input.value = config_path
            out_root_input.value = out_root

            req = RunRequest(
                config_path=config_path,
                out_root=out_root,
                pages=int(pages_input.value or 0),
                workers=int(workers_input.value or 0),
                seed=int(seed_input.value or -1),
                smoke_test=bool(smoke_test_input.value),
                overrides=_collect_overrides(),
            )
            current_run_id = orchestrator.start(req)

            run_id_label.text = current_run_id
            state_label.text = 'running'
            progress_label.text = 'started'

            stdout_log.value = ''
            stderr_log.value = ''
            status_json.value = ''
            summary_json.value = ''

            start_btn.disable()
            stop_btn.enable()

            ui.notify(f'Run started: {current_run_id}', color='positive')

        except Exception as e:
            ui.notify(f'Run start failed: {e}', color='negative')


def _stop_run() -> None:
    global current_run_id

    if not current_run_id:
        return
    ok = orchestrator.cancel(current_run_id)
    if ok:
        state_label.text = 'cancelled'
        start_btn.enable()
        stop_btn.disable()
        ui.notify('Run cancelled', color='warning')


def _open_output_folder() -> None:
    if not current_run_id:
        return
    try:
        summary = orchestrator.get_summary(current_run_id)
        if summary.out_root:
            _open_path(summary.out_root)
    except Exception as e:
        ui.notify(f'Open output failed: {e}', color='negative')


def _open_qc_summary() -> None:
    if not current_run_id:
        return
    try:
        summary = orchestrator.get_summary(current_run_id)
        if summary.qc_summary_path:
            _open_path(summary.qc_summary_path)
    except Exception as e:
        ui.notify(f'Open qc_summary failed: {e}', color='negative')


def _open_run_log() -> None:
    if not current_run_id:
        return
    try:
        summary = orchestrator.get_summary(current_run_id)
        if summary.run_log_path:
            _open_path(summary.run_log_path)
    except Exception as e:
        ui.notify(f'Open run.log failed: {e}', color='negative')

def _recipe_csv_path() -> str:
    config_path = _normalize_config_path(str(config_path_input.value or ""))
    return str(Path(config_path).with_suffix(".recipe.csv"))


def _export_recipe_csv() -> None:
    try:
        rows = []

        rows.append({"section": "run", "key": "config_path", "value": _normalize_config_path(str(config_path_input.value or ""))})
        rows.append({"section": "run", "key": "out_root", "value": _normalize_out_root(str(out_root_input.value or ""))})
        rows.append({"section": "run", "key": "pages", "value": int(pages_input.value or 0)})
        rows.append({"section": "run", "key": "workers", "value": int(workers_input.value or 0)})
        rows.append({"section": "run", "key": "seed", "value": int(seed_input.value or -1)})
        rows.append({"section": "run", "key": "smoke_test", "value": bool(smoke_test_input.value)})

        for key, widget in field_widgets.items():
            value = _read_widget_value(key, widget)
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            rows.append({"section": "field", "key": key, "value": value})

        raw_yaml_text = ""
        if raw_yaml_override_input is not None:
            raw_yaml_text = str(raw_yaml_override_input.value or "").strip()

        if raw_yaml_text:
            rows.append({"section": "raw_yaml", "key": "raw_yaml_override", "value": raw_yaml_text})

        csv_path = _recipe_csv_path()
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["section", "key", "value"])
            writer.writeheader()
            writer.writerows(rows)

        ui.notify(f"CSV exported: {csv_path}", color="positive")
    except Exception as e:
        ui.notify(f"CSV export failed: {e}", color="negative")


def _open_recipe_csv() -> None:
    try:
        csv_path = _recipe_csv_path()
        if not Path(csv_path).exists():
            ui.notify("CSV not found. Export it first.", color="warning")
            return
        _open_path(csv_path)
    except Exception as e:
        ui.notify(f"Open CSV failed: {e}", color="negative")


def _apply_recipe_csv_rows(rows: list[dict[str, str]]) -> None:
    global _csv_loading_mode

    override_map: Dict[str, Any] = {}
    raw_yaml_parts: list[str] = []

    pending_config_path: Optional[str] = None
    pending_out_root: Optional[str] = None
    pending_pages: Optional[int] = None
    pending_workers: Optional[int] = None
    pending_seed: Optional[int] = None
    pending_smoke_test: Optional[bool] = None

    _csv_loading_mode = True
    try:
        for row in rows:
            section = str(row.get("section", "")).strip().lower()
            key = str(row.get("key", "")).strip()
            value = row.get("value", "")

            if section == "run":
                if key == "config_path":
                    pending_config_path = _normalize_config_path(str(value or ""))
                elif key == "out_root":
                    pending_out_root = _normalize_out_root(str(value or ""))
                elif key == "pages":
                    pending_pages = int(value or 0)
                elif key == "workers":
                    pending_workers = int(value or 0)
                elif key == "seed":
                    pending_seed = int(value or -1)
                elif key == "smoke_test":
                    pending_smoke_test = str(value).strip().lower() in {"1", "true", "yes", "on"}

            elif section == "field":
                field = SCHEMA_MAP.get(key, {})
                field_type = field.get("field_type", "str")

                parsed: Any = value
                try:
                    if field_type == "bool":
                        parsed = str(value).strip().lower() in {"1", "true", "yes", "on"}
                    elif field_type == "int":
                        parsed = int(value)
                    elif field_type == "float":
                        parsed = float(value)
                    elif field_type in {"json", "color_rgb"}:
                        try:
                            parsed = json.loads(value)
                        except Exception:
                            parsed = value
                except Exception:
                    parsed = value

                override_map[key] = parsed

            elif section == "raw_yaml":
                txt = str(value or "").strip()
                if txt:
                    raw_yaml_parts.append(txt)

        if pending_config_path is not None:
            config_path_input.value = pending_config_path
            _load_baseline_and_user_config()

        if pending_out_root is not None:
            out_root_input.value = pending_out_root
        if pending_pages is not None:
            pages_input.value = pending_pages
        if pending_workers is not None:
            workers_input.value = pending_workers
        if pending_seed is not None:
            seed_input.value = pending_seed
        if pending_smoke_test is not None:
            smoke_test_input.value = pending_smoke_test

        _load_form_from_override_map(override_map)

        if raw_yaml_override_input is not None:
            raw_yaml_override_input.value = "\n\n".join(raw_yaml_parts).strip()

        _refresh_effective_yaml_preview()

    finally:
        _csv_loading_mode = False



def _handle_recipe_csv_upload(e: Any) -> None:
    try:
        uploaded_bytes = e.content.read()
        text = uploaded_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)

        if not rows:
            ui.notify("CSV is empty", color="warning")
            return

        _apply_recipe_csv_rows(rows)
        ui.notify("CSV loaded into form", color="positive")
    except Exception as ex:
        ui.notify(f"CSV load failed: {ex}", color="negative")

# -------------------------
# PAGE
# -------------------------
ui.dark_mode().enable()

with ui.header().classes('items-center justify-between'):
    ui.label('AI1 Gen | Web GUI').classes('text-xl font-bold')
    with ui.row():
        ui.button('Refresh', on_click=_refresh_status_panels, icon='refresh')
        ui.button('Open Output', on_click=_open_output_folder, icon='folder_open')

with ui.row().classes('w-full no-wrap items-start'):
    with ui.column().classes('w-1/2 p-2'):
        with ui.card().classes('w-full'):
            ui.label('Run').classes('text-lg font-semibold')

            config_path_input = ui.input(
                'Config Path',
                value=str(_DEFAULT_CONFIG.resolve())
            ).classes('w-full')
            config_path_input.on_value_change(_on_config_path_change)

            out_root_input = ui.input(
                'Output Root',
                value=str((_PROJECT_ROOT / "out" / "web_gui").resolve())
            ).classes('w-full')
            out_root_input.on_value_change(_on_any_field_change)

            with ui.row().classes('w-full'):
                pages_input = ui.number('Pages', value=100, step=1).classes('w-1/3')
                workers_input = ui.number('Workers', value=4, step=1).classes('w-1/3')
                seed_input = ui.number('Seed', value=1337, step=1).classes('w-1/3')

            pages_input.on_value_change(_on_any_field_change)
            workers_input.on_value_change(_on_any_field_change)
            seed_input.on_value_change(_on_any_field_change)

            smoke_test_input = ui.switch('Smoke Test', value=False)
            smoke_test_input.on_value_change(_on_any_field_change)

            with ui.row():
                start_btn = ui.button('Start Run', on_click=_start_run, icon='play_arrow')
                stop_btn = ui.button('Stop Run', on_click=_stop_run, icon='stop')
                stop_btn.disable()

        with ui.card().classes('w-full'):
            ui.label('CSV Recipe').classes('text-lg font-semibold')

            with ui.row():
                ui.button('Export CSV', on_click=_export_recipe_csv, icon='download')
                ui.button('Open CSV', on_click=_open_recipe_csv, icon='table_view')

            csv_upload_widget = ui.upload(
                on_upload=_handle_recipe_csv_upload,
                auto_upload=True,
            ).props('accept=.csv').classes('w-full')        
        
        
        
        
        with ui.tabs().classes('w-full') as tabs:
            basic_tab = ui.tab('Basic')
            advanced_tab = ui.tab('Advanced')

        with ui.tab_panels(tabs, value=basic_tab).classes('w-full'):
            with ui.tab_panel(basic_tab):
                _build_grouped_fields(orchestrator.get_schema_for_ui("basic"))

            with ui.tab_panel(advanced_tab):
                with ui.card().classes('w-full'):
                    ui.label('Advanced Config Manager').classes('text-lg font-semibold')

                    user_yaml_path_label = ui.label('-').classes('text-sm text-gray-500')

                    with ui.row():
                        ui.button('Reload YAML', on_click=_reload_from_yaml_files, icon='refresh')
                        ui.button('Save Advanced', on_click=_save_advanced_to_user_yaml, icon='save')
                        ui.button('Reset Advanced', on_click=_reset_advanced_to_baseline, icon='restore')

                    raw_yaml_override_input = ui.textarea(
                        label='Raw YAML Override',
                        value='',
                    ).classes('w-full').props('rows=10')
                    raw_yaml_override_input.on_value_change(lambda e: _refresh_effective_yaml_preview())

                    effective_yaml_preview = ui.textarea(
                        label='Effective YAML Preview',
                        value='',
                    ).classes('w-full').props('rows=20 readonly')

                _build_grouped_fields(orchestrator.get_schema_for_ui("advanced"))

    with ui.column().classes('w-1/2 p-2'):
        with ui.card().classes('w-full'):
            ui.label('Status').classes('text-lg font-semibold')
            run_id_label = ui.label('-')
            state_label = ui.label('idle')
            pid_label = ui.label('-')
            return_code_label = ui.label('-')
            out_root_label = ui.label('-')
            progress_label = ui.label('-')

        with ui.card().classes('w-full'):
            ui.label('Outputs / Summary').classes('text-lg font-semibold')
            with ui.row():
                ui.button('Open qc_summary.json', on_click=_open_qc_summary, icon='description')
                ui.button('Open run.log', on_click=_open_run_log, icon='article')
            summary_json = ui.codemirror(
                value='',
                language='JSON',
            ).classes('w-full').style('height: 260px')

        with ui.card().classes('w-full'):
            ui.label('Status JSON').classes('text-lg font-semibold')
            status_json = ui.codemirror(
                value='',
                language='JSON',
            ).classes('w-full').style('height: 220px')

        with ui.card().classes('w-full'):
            ui.label('stdout').classes('text-lg font-semibold')
            stdout_log = ui.codemirror(
                value='',
                language='text',
            ).classes('w-full').style('height: 220px')

        with ui.card().classes('w-full'):
            ui.label('stderr').classes('text-lg font-semibold')
            stderr_log = ui.codemirror(
                value='',
                language='text',
            ).classes('w-full').style('height: 220px')

_load_baseline_and_user_config()
ui.timer(1.5, _refresh_status_panels)


def main() -> None:
    ui.run(
        title='AI1 Gen Web GUI',
        host='0.0.0.0',
        port=8080,
        reload=False,
    )


if __name__ in {'__main__', '__mp_main__'}:
    main()