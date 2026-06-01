# src/ai1_gen/gui/web/template_csv.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - nicegui>=2.0,<3.0

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Dict

from nicegui import ui

from ai1_gen.gui.shared.paths import normalize_out_root, open_path, WEB_GUI_OUT_DIR
from ai1_gen.gui.shared.upload_utils import read_upload_bytes

from .constants import CSV_EXPORT_DELIMITER
from .presets import TEMPLATE_COLUMNS, TEMPLATE_REGION_TYPES, SAMPLE_TEMPLATE_ROWS
from .state import WebGuiState


def parse_template_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


def parse_template_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def parse_template_int_or_blank(value: Any) -> Any:
    txt = str(value or "").strip()

    if not txt:
        return ""

    try:
        return int(float(txt))
    except Exception:
        return txt


def coerce_template_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out = {col: row.get(col, "") for col in TEMPLATE_COLUMNS}

    out["template_name"] = str(out.get("template_name") or "custom_template").strip() or "custom_template"
    out["page_no"] = int(parse_template_int_or_blank(out.get("page_no") or 1) or 1)
    out["region_id"] = str(out.get("region_id") or "region").strip() or "region"
    out["type"] = str(out.get("type") or "text_block").strip() or "text_block"

    if out["type"] not in TEMPLATE_REGION_TYPES:
        out["type"] = "text_block"

    out["label"] = str(out.get("label") or out["region_id"]).strip()

    out["x"] = max(0.0, min(1.0, parse_template_float(out.get("x"), 0.05)))
    out["y"] = max(0.0, min(1.0, parse_template_float(out.get("y"), 0.05)))
    out["w"] = max(0.01, min(1.0, parse_template_float(out.get("w"), 0.30)))
    out["h"] = max(0.01, min(1.0, parse_template_float(out.get("h"), 0.08)))

    if out["x"] + out["w"] > 1.0:
        out["w"] = max(0.01, 1.0 - out["x"])

    if out["y"] + out["h"] > 1.0:
        out["h"] = max(0.01, 1.0 - out["y"])

    out["content_source"] = str(out.get("content_source") or "").strip()
    out["min_rows"] = parse_template_int_or_blank(out.get("min_rows"))
    out["max_rows"] = parse_template_int_or_blank(out.get("max_rows"))
    out["cols"] = parse_template_int_or_blank(out.get("cols"))
    out["required"] = parse_template_bool(out.get("required"))
    out["jitter"] = max(0.0, min(0.20, parse_template_float(out.get("jitter"), 0.01)))
    out["style_hint"] = str(out.get("style_hint") or "normal_block").strip()
    out["mask_role"] = str(out.get("mask_role") or "text").strip()
    out["annotation_label"] = str(out.get("annotation_label") or out["label"]).strip()

    return out


def template_output_path(state: WebGuiState) -> Path:
    out_root = (
        normalize_out_root(str(state.out_root_input.value or ""))
        if state.out_root_input is not None
        else ""
    )

    base = Path(out_root) if out_root else WEB_GUI_OUT_DIR
    return base / "template_regions.csv"


def strip_excel_sep_line(text: str) -> str:
    lines = str(text or "").splitlines()

    if lines and lines[0].strip().lower().startswith("sep="):
        return "\n".join(lines[1:])

    return str(text or "")


def make_csv_reader(text: str) -> csv.DictReader:
    clean_text = strip_excel_sep_line(text)
    sample = clean_text[:4096]

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    except Exception:
        dialect = csv.excel
        dialect.delimiter = CSV_EXPORT_DELIMITER

    return csv.DictReader(io.StringIO(clean_text), dialect=dialect)


async def handle_template_csv_upload(state: WebGuiState, e: Any, *, on_loaded=None) -> None:
    try:
        uploaded_bytes = await read_upload_bytes(e)
        text = uploaded_bytes.decode("utf-8-sig", errors="replace")

        reader = make_csv_reader(text)
        rows = [coerce_template_row(dict(r)) for r in reader]

        if not rows:
            ui.notify("Template CSV is empty", color="warning")
            return

        state.template_rows = rows

        names = available_template_names(state)
        state.active_template_name = names[0] if names else None

        active_rows = active_template_rows(state)
        state.selected_template_region_id = (
            str(active_rows[0].get("region_id"))
            if active_rows
            else None
        )

        if state.document_template_select is not None:
            state.document_template_select.value = "Custom CSV template"

        if on_loaded is not None:
            on_loaded()

        ui.notify(f"Template CSV loaded: {len(state.template_rows)} regions", color="positive")

    except Exception as ex:
        ui.notify(f"Template CSV load failed: {ex}", color="negative")


def export_template_csv_example(state: WebGuiState) -> None:
    try:
        path = template_output_path(state)
        path.parent.mkdir(parents=True, exist_ok=True)

        rows = state.template_rows if state.template_rows else [
            coerce_template_row(dict(r)) for r in SAMPLE_TEMPLATE_ROWS
        ]

        with path.open("w", newline="", encoding="utf-8-sig") as f:
            f.write(f"sep={CSV_EXPORT_DELIMITER}\n")

            writer = csv.DictWriter(
                f,
                fieldnames=TEMPLATE_COLUMNS,
                delimiter=CSV_EXPORT_DELIMITER,
            )
            writer.writeheader()

            for row in rows:
                writer.writerow({col: row.get(col, "") for col in TEMPLATE_COLUMNS})

        ui.notify(f"Template CSV saved: {path}", color="positive")

    except Exception as e:
        ui.notify(f"Template CSV export failed: {e}", color="negative")


def open_template_csv(state: WebGuiState) -> None:
    path = template_output_path(state)

    if not path.exists():
        ui.notify("Template CSV not found. Export it first.", color="warning")
        return

    open_path(str(path))


def available_template_names(state: WebGuiState) -> list[str]:
    return sorted(
        {
            str(row.get("template_name") or "custom_template").strip()
            or "custom_template"
            for row in state.template_rows
        }
    )


def get_active_template_name(state: WebGuiState) -> str | None:
    names = available_template_names(state)

    if not names:
        state.active_template_name = None
        return None

    if state.active_template_name not in names:
        state.active_template_name = names[0]

    return state.active_template_name


def active_template_rows(state: WebGuiState) -> list[Dict[str, Any]]:
    name = get_active_template_name(state)

    if not name:
        return []

    return [
        row
        for row in state.template_rows
        if str(row.get("template_name") or "custom_template").strip() == name
    ]