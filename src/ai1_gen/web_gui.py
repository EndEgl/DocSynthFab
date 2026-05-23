# src/ai1_gen/web_gui.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - nicegui>=2.0,<3.0
# - PyYAML>=6.0,<7.0

from __future__ import annotations

import csv
import io
import json
import os
import sys
import threading
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional, List

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
from ai1_gen.content import reset_content_to_samples, ensure_content_bank


# ---------------------------------------------------------
# Runtime state
# ---------------------------------------------------------

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

template_csv_upload_widget = None
document_template_select = None
template_name_select = None
template_region_select = None
template_preview_html = None
template_editor_preview_html = None
template_region_type_select = None
template_region_label_input = None
template_region_content_source_input = None
template_region_x_input = None
template_region_y_input = None
template_region_w_input = None
template_region_h_input = None
template_region_min_rows_input = None
template_region_max_rows_input = None
template_region_cols_input = None
template_region_required_switch = None
template_region_jitter_input = None
template_status_label = None

template_rows: List[Dict[str, Any]] = []
active_template_name: Optional[str] = None
selected_template_region_id: Optional[str] = None


content_source_mode_select = None

# User-friendly simple controls
dataset_goal_select = None
dataset_character_select = None
content_mix_select = None
text_length_select = None
table_amount_select = None
variation_select = None
diversity_strength_select = None
preview_html = None
preview_caption = None
simple_summary_label = None

baseline_overrides: Dict[str, Any] = {}
_csv_loading_mode = False

# Excel'in Türkçe/Avrupa bölgesel ayarlarında CSV sütunları genelde noktalı virgül ile ayrılır.
# Bu yüzden export tarafında ; kullanıyoruz; import tarafında ise hem ; hem , destekliyoruz.
CSV_EXPORT_DELIMITER = ";"


# ---------------------------------------------------------
# User-friendly preset layer
# ---------------------------------------------------------

DATASET_GOAL_PRESETS: Dict[str, Dict[str, Any]] = {
    "Quick OCR Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "words",
    },
    "Layout + OCR Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "sentences",
    },
    "Math Document Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "sentences",
        "content.has_equation_prob": 0.45,
        "content.has_table_prob": 0.10,
        "content.has_figure_prob": 0.03,
    },
    "Table-heavy Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "sentences",
        "content.has_equation_prob": 0.08,
        "content.has_table_prob": 0.50,
        "content.has_figure_prob": 0.05,
    },
    "Full Document AI Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "sentences",
        "content.has_equation_prob": 0.22,
        "content.has_table_prob": 0.25,
        "content.has_figure_prob": 0.12,
    },
}

DATASET_CHARACTER_PRESETS: Dict[str, Dict[str, Any]] = {
    "Clean": {
        "dist.noise_level_dist": {"clean": 0.85, "medium": 0.15, "heavy": 0.00},
        "augment.enable": True,
    },
    "Balanced": {
        "dist.noise_level_dist": {"clean": 0.35, "medium": 0.50, "heavy": 0.15},
        "augment.enable": True,
    },
    "Realistic Scan": {
        "dist.noise_level_dist": {"clean": 0.20, "medium": 0.55, "heavy": 0.25},
        "augment.enable": True,
    },
    "Stress Test": {
        "dist.noise_level_dist": {"clean": 0.05, "medium": 0.35, "heavy": 0.60},
        "augment.enable": True,
    },
}

CONTENT_MIX_PRESETS: Dict[str, Dict[str, Any]] = {
    "Mostly Text": {
        "content.has_equation_prob": 0.05,
        "content.has_table_prob": 0.08,
        "content.has_figure_prob": 0.03,
    },
    "Text + Math": {
        "content.has_equation_prob": 0.40,
        "content.has_table_prob": 0.10,
        "content.has_figure_prob": 0.03,
    },
    "Text + Tables": {
        "content.has_equation_prob": 0.08,
        "content.has_table_prob": 0.45,
        "content.has_figure_prob": 0.04,
    },
    "Mixed Document AI": {
        "content.has_equation_prob": 0.22,
        "content.has_table_prob": 0.25,
        "content.has_figure_prob": 0.10,
    },
}

VARIATION_PRESETS: Dict[str, Dict[str, Any]] = {
    "Low": {
        "dist.density_dist": {"sparse": 0.25, "normal": 0.65, "dense": 0.10},
    },
    "Medium": {
        "dist.density_dist": {"sparse": 0.20, "normal": 0.55, "dense": 0.25},
    },
    "High": {
        "dist.density_dist": {"sparse": 0.22, "normal": 0.38, "dense": 0.40},
    },
}

DIVERSITY_STRENGTH_PRESETS: Dict[str, Dict[str, Any]] = {
    "Balanced diversity": {
        "diversity_preset": "balanced_document_ai_diverse",

        "content.has_equation_prob": 0.38,
        "content.has_table_prob": 0.38,
        "content.has_figure_prob": 0.12,

        "dist.density_dist": {
            "sparse": 0.20,
            "normal": 0.40,
            "dense": 0.30,
            "mixed": 0.10,
        },
        "dist.noise_level_dist": {
            "clean": 0.30,
            "medium": 0.45,
            "heavy": 0.25,
        },
        "layout.layout_type_dist": {
            "single_col": 0.28,
            "double_col": 0.24,
            "mixed_cols": 0.28,
            "academic": 0.12,
            "report_like": 0.08,
        },
        "render.text.scripts_dist": {
            "latin": 0.42,
            "tr": 0.20,
            "de": 0.06,
            "ru": 0.10,
            "el": 0.06,
            "ar": 0.07,
            "symbols": 0.09,
        },
    },

    "High diversity": {
        "diversity_preset": "high_document_ai_diverse",

        "content.has_equation_prob": 0.45,
        "content.has_table_prob": 0.45,
        "content.has_figure_prob": 0.16,
        "content.has_caption_prob": 0.45,

        "dist.density_dist": {
            "sparse": 0.22,
            "normal": 0.32,
            "dense": 0.32,
            "mixed": 0.14,
        },
        "dist.noise_level_dist": {
            "clean": 0.22,
            "medium": 0.48,
            "heavy": 0.30,
        },
        "layout.layout_type_dist": {
            "single_col": 0.22,
            "double_col": 0.24,
            "mixed_cols": 0.34,
            "academic": 0.12,
            "report_like": 0.08,
        },
        "render.text.scripts_dist": {
            "latin": 0.34,
            "tr": 0.20,
            "de": 0.07,
            "ru": 0.12,
            "el": 0.08,
            "ar": 0.09,
            "symbols": 0.10,
        },
        "render.latex.complexity_mix": {
            "simple": 0.25,
            "medium": 0.45,
            "complex": 0.30,
        },
        "render.non_text.table_size_mix": {
            "small": 0.28,
            "medium": 0.42,
            "large": 0.30,
        },
    },

    "Max diversity / stress": {
        "diversity_preset": "max_document_ai_diverse_stress",

        "content.has_equation_prob": 0.55,
        "content.has_table_prob": 0.55,
        "content.has_figure_prob": 0.22,
        "content.has_caption_prob": 0.55,

        "dist.density_dist": {
            "sparse": 0.24,
            "normal": 0.26,
            "dense": 0.34,
            "mixed": 0.16,
        },
        "dist.noise_level_dist": {
            "clean": 0.15,
            "medium": 0.45,
            "heavy": 0.40,
        },
        "layout.layout_type_dist": {
            "single_col": 0.18,
            "double_col": 0.24,
            "mixed_cols": 0.38,
            "academic": 0.12,
            "report_like": 0.08,
        },
        "render.text.scripts_dist": {
            "latin": 0.28,
            "tr": 0.18,
            "de": 0.08,
            "ru": 0.14,
            "el": 0.09,
            "ar": 0.11,
            "symbols": 0.12,
        },
        "render.latex.complexity_mix": {
            "simple": 0.18,
            "medium": 0.42,
            "complex": 0.40,
        },
        "render.non_text.table_size_mix": {
            "small": 0.30,
            "medium": 0.35,
            "large": 0.35,
        },
        "augment.selection_policy.heavy.p_capture": 0.65,
        "augment.selection_policy.heavy.p_blur_noise": 0.68,
        "augment.selection_policy.heavy.p_geometry": 0.50,
    },
}

TEXT_LENGTH_PRESETS: Dict[str, Dict[str, Any]] = {
    "Short blocks": {
        "content.text_mode": "words",
    },
    "Balanced blocks": {
        "content.text_mode": "mixed",
    },
    "Long paragraphs": {
        "content.text_mode": "sentences",
    },
}

TABLE_AMOUNT_PRESETS: Dict[str, Dict[str, Any]] = {
    "No tables": {
        "content.has_table_prob": 0.02,
    },
    "Some tables": {
        "content.has_table_prob": 0.15,
    },
    "Many tables": {
        "content.has_table_prob": 0.45,
    },
    "Table-heavy": {
        "content.has_table_prob": 0.70,
    },
}

DOCUMENT_TEMPLATE_PRESETS: Dict[str, Dict[str, Any]] = {
    "Generic random document": {},
    "Invoice": {
        "content.has_table_prob": 0.65,
        "content.has_equation_prob": 0.02,
        "content.has_figure_prob": 0.03,
        "content.text_mode": "sentences",
        "dist.density_dist": {"sparse": 0.10, "normal": 0.50, "dense": 0.40},
    },
    "Delivery note": {
        "content.has_table_prob": 0.55,
        "content.has_equation_prob": 0.02,
        "content.has_figure_prob": 0.03,
        "content.text_mode": "sentences",
    },
    "Customs declaration": {
        "content.has_table_prob": 0.75,
        "content.has_equation_prob": 0.01,
        "content.has_figure_prob": 0.02,
        "content.text_mode": "sentences",
        "dist.density_dist": {"sparse": 0.05, "normal": 0.35, "dense": 0.60},
    },
    "Exam sheet": {
        "content.has_table_prob": 0.08,
        "content.has_equation_prob": 0.35,
        "content.has_figure_prob": 0.05,
        "content.text_mode": "sentences",
    },
    "Contract page": {
        "content.has_table_prob": 0.03,
        "content.has_equation_prob": 0.00,
        "content.has_figure_prob": 0.02,
        "content.text_mode": "sentences",
        "dist.density_dist": {"sparse": 0.10, "normal": 0.55, "dense": 0.35},
    },
    "Inspection checklist": {
        "content.has_table_prob": 0.55,
        "content.has_equation_prob": 0.02,
        "content.has_figure_prob": 0.04,
        "content.text_mode": "sentences",
    },
    "Custom CSV template": {},
}

TEMPLATE_REGION_TYPES = [
    "text_block",
    "field",
    "table",
    "checkbox",
    "checkbox_group",
    "signature",
    "stamp",
    "figure",
    "separator",
    "empty_box",
    "barcode_like",
    "qr_like",
    "numbered_list",
    "bullet_list",
    "paragraph",
    "math_block",
    "header",
    "footer",
]

TEMPLATE_COLUMNS = [
    "template_name",
    "page_no",
    "region_id",
    "type",
    "label",
    "x",
    "y",
    "w",
    "h",
    "content_source",
    "min_rows",
    "max_rows",
    "cols",
    "required",
    "jitter",
    "style_hint",
    "mask_role",
    "annotation_label",
]

SAMPLE_TEMPLATE_ROWS: List[Dict[str, Any]] = [
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "title",
        "type": "header",
        "label": "document_title",
        "x": 0.05,
        "y": 0.04,
        "w": 0.45,
        "h": 0.05,
        "content_source": "doc_titles",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": True,
        "jitter": 0.005,
        "style_hint": "bold_header",
        "mask_role": "text",
        "annotation_label": "title",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "seller",
        "type": "text_block",
        "label": "seller_info",
        "x": 0.05,
        "y": 0.11,
        "w": 0.42,
        "h": 0.12,
        "content_source": "company_info",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": True,
        "jitter": 0.01,
        "style_hint": "normal_block",
        "mask_role": "text",
        "annotation_label": "seller_info",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "invoice_no",
        "type": "field",
        "label": "invoice_number",
        "x": 0.66,
        "y": 0.05,
        "w": 0.26,
        "h": 0.04,
        "content_source": "invoice_numbers",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": True,
        "jitter": 0.005,
        "style_hint": "small_field",
        "mask_role": "text",
        "annotation_label": "invoice_number",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "items",
        "type": "table",
        "label": "items_table",
        "x": 0.05,
        "y": 0.30,
        "w": 0.90,
        "h": 0.38,
        "content_source": "product_rows",
        "min_rows": 4,
        "max_rows": 12,
        "cols": 6,
        "required": True,
        "jitter": 0.01,
        "style_hint": "bordered_table",
        "mask_role": "text",
        "annotation_label": "items_table",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "signature",
        "type": "signature",
        "label": "signature_area",
        "x": 0.62,
        "y": 0.82,
        "w": 0.28,
        "h": 0.08,
        "content_source": "signatures",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": False,
        "jitter": 0.01,
        "style_hint": "signature_box",
        "mask_role": "text",
        "annotation_label": "signature",
    },
]


# ---------------------------------------------------------
# Path / parsing helpers
# ---------------------------------------------------------

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


def _merge_maps(*maps: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for m in maps:
        out.update(m or {})
    return out


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


def _collect_simple_overrides() -> Dict[str, Any]:
    if dataset_goal_select is None:
        return {}

    goal = str(dataset_goal_select.value or "Quick OCR Dataset")
    character = str(dataset_character_select.value or "Balanced")
    content_mix = str(content_mix_select.value or "Mostly Text")
    text_length = str(text_length_select.value or "Balanced blocks")
    table_amount = str(table_amount_select.value or "Some tables")
    variation = str(variation_select.value or "Medium")

    diversity_strength = str(
        diversity_strength_select.value or "Balanced diversity"
    ) if diversity_strength_select is not None else "Balanced diversity"

    return _merge_maps(
        DOCUMENT_TEMPLATE_PRESETS.get(
            str(document_template_select.value or "Generic random document")
            if document_template_select is not None else "Generic random document",
            {},
        ),
        DATASET_GOAL_PRESETS.get(goal, {}),
        DATASET_CHARACTER_PRESETS.get(character, {}),
        CONTENT_MIX_PRESETS.get(content_mix, {}),
        TEXT_LENGTH_PRESETS.get(text_length, {}),
        TABLE_AMOUNT_PRESETS.get(table_amount, {}),
        VARIATION_PRESETS.get(variation, {}),
        DIVERSITY_STRENGTH_PRESETS.get(diversity_strength, {}),
    )

def _collect_all_overrides_for_run() -> Dict[str, Any]:
    # Advanced alanlar korunur. Simple presetler sonradan merge edilir.
    # Böylece ana kullanıcı akışı belirleyici olur, power-user alanları da kaybolmaz.
    overrides = _collect_overrides()
    overrides.update(_collect_simple_overrides())

    if content_source_mode_select is not None:
        mode = str(content_source_mode_select.value or "content_bank")
        overrides["content.source_mode"] = mode
        if mode == "random_chars":
            overrides["content.text_mode"] = "chars"

    return overrides


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


# ---------------------------------------------------------
# Effective YAML / config helpers
# ---------------------------------------------------------

def _build_current_effective_yaml() -> str:
    config_path = _normalize_config_path(str(config_path_input.value or ""))
    out_root = _normalize_out_root(str(out_root_input.value or ""))

    raw_yaml_text = ""
    if raw_yaml_override_input is not None:
        raw_yaml_text = str(raw_yaml_override_input.value or "")

    overrides = _collect_all_overrides_for_run()

    return orchestrator.build_effective_config_yaml_text(
        config_path=config_path,
        overrides=overrides,
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


# ---------------------------------------------------------
# UX preview helpers
# ---------------------------------------------------------

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
        line_groups = [max(3, x - 2) if i % 2 == 0 else x + 2 for i, x in enumerate(base_groups + [6])]
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
    table_rows = {"Some tables": 3, "Many tables": 4, "Table-heavy": 5}.get(table_amount, 0)

    noisy = character in {"Realistic Scan", "Stress Test"}
    heavy = character == "Stress Test"

    parts = []
    parts.append(f'''
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
         xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="{width}" height="{height}" rx="22" fill="#111827"/>
      <rect x="22" y="22" width="{width-44}" height="{height-44}" rx="14"
            fill="#ffffff" stroke="#d1d5db" stroke-width="2"/>
      <rect x="{margin}" y="{margin}" width="{width-2*margin}" height="{height-2*margin}"
            fill="none" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="5 5"/>
    ''')

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
                f'stroke="#374151" stroke-width="2.2" stroke-linecap="round" opacity="0.72"/>'
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
            th = 58 + table_rows * 10
            parts.append(
                f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" '
                f'rx="8" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>'
            )
            grid_rows = max(2, table_rows)
            for k in range(1, grid_rows + 1):
                parts.append(
                    f'<line x1="{tx}" y1="{ty+k*th/(grid_rows+1)}" x2="{tx+tw}" y2="{ty+k*th/(grid_rows+1)}" '
                    f'stroke="#2563eb" stroke-width="1" opacity="0.55"/>'
                )
            for k in range(1, 4):
                parts.append(
                    f'<line x1="{tx+k*tw/4}" y1="{ty}" x2="{tx+k*tw/4}" y2="{ty+th}" '
                    f'stroke="#2563eb" stroke-width="1" opacity="0.55"/>'
                )
            parts.append(
                f'<text x="{tx+14}" y="{ty+22}" font-size="12" fill="#1d4ed8">table region</text>'
            )
            y += th + 24

        if has_figure and block_id == 3:
            parts.append(
                f'<rect x="{margin+22}" y="{y}" width="{width-2*margin-44}" height="84" '
                f'rx="12" fill="#f3f4f6" stroke="#6b7280" stroke-width="2" stroke-dasharray="7 5"/>'
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
        parts.append(
            f'<circle cx="320" cy="86" r="20" fill="#111827" opacity="0.06"/>'
        )

    if heavy:
        parts.append(
            f'<line x1="58" y1="38" x2="84" y2="{height-62}" '
            f'stroke="#111827" stroke-width="4" opacity="0.11"/>'
        )
        parts.append(
            f'<rect x="22" y="{height-100}" width="{width-44}" height="26" '
            f'fill="#111827" opacity="0.07"/>'
        )

    parts.append("</svg>")
    return "".join(parts)


def _update_preview() -> None:
    if preview_html is None or dataset_goal_select is None:
        return

    goal = str(dataset_goal_select.value or "Quick OCR Dataset")
    character = str(dataset_character_select.value or "Balanced")
    content_mix = str(content_mix_select.value or "Mostly Text")
    text_length = str(text_length_select.value or "Balanced blocks")
    table_amount = str(table_amount_select.value or "Some tables")
    variation = str(variation_select.value or "Medium")

    diversity_strength = str(
        diversity_strength_select.value or "Balanced diversity"
    ) if diversity_strength_select is not None else "Balanced diversity"

    preview_html.set_content(
        _wireframe_svg(
            goal=goal,
            character=character,
            content_mix=content_mix,
            text_length=text_length,
            table_amount=table_amount,
            variation=variation,
        )
    )

    if simple_summary_label is not None:
        simple_summary_label.text = (
            f"Preset summary: {goal} with {character.lower()} visual character, "
            f"{content_mix.lower()} content, {text_length.lower()}, "
            f"{table_amount.lower()}, {variation.lower()} variation, "
            f"and {diversity_strength.lower()}."
        )


    _refresh_effective_yaml_preview()


# ---------------------------------------------------------
# Custom template CSV helpers
# ---------------------------------------------------------

def _parse_template_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


def _parse_template_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _parse_template_int_or_blank(value: Any) -> Any:
    txt = str(value or "").strip()
    if not txt:
        return ""
    try:
        return int(float(txt))
    except Exception:
        return txt


def _coerce_template_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out = {col: row.get(col, "") for col in TEMPLATE_COLUMNS}
    out["template_name"] = str(out.get("template_name") or "custom_template").strip() or "custom_template"
    out["page_no"] = int(_parse_template_int_or_blank(out.get("page_no") or 1) or 1)
    out["region_id"] = str(out.get("region_id") or "region").strip() or "region"
    out["type"] = str(out.get("type") or "text_block").strip() or "text_block"
    if out["type"] not in TEMPLATE_REGION_TYPES:
        out["type"] = "text_block"
    out["label"] = str(out.get("label") or out["region_id"]).strip()
    out["x"] = max(0.0, min(1.0, _parse_template_float(out.get("x"), 0.05)))
    out["y"] = max(0.0, min(1.0, _parse_template_float(out.get("y"), 0.05)))
    out["w"] = max(0.01, min(1.0, _parse_template_float(out.get("w"), 0.30)))
    out["h"] = max(0.01, min(1.0, _parse_template_float(out.get("h"), 0.08)))
    if out["x"] + out["w"] > 1.0:
        out["w"] = max(0.01, 1.0 - out["x"])
    if out["y"] + out["h"] > 1.0:
        out["h"] = max(0.01, 1.0 - out["y"])
    out["content_source"] = str(out.get("content_source") or "").strip()
    out["min_rows"] = _parse_template_int_or_blank(out.get("min_rows"))
    out["max_rows"] = _parse_template_int_or_blank(out.get("max_rows"))
    out["cols"] = _parse_template_int_or_blank(out.get("cols"))
    out["required"] = _parse_template_bool(out.get("required"))
    out["jitter"] = max(0.0, min(0.20, _parse_template_float(out.get("jitter"), 0.01)))
    out["style_hint"] = str(out.get("style_hint") or "normal_block").strip()
    out["mask_role"] = str(out.get("mask_role") or "text").strip()
    out["annotation_label"] = str(out.get("annotation_label") or out["label"]).strip()
    return out


def _template_output_path() -> Path:
    out_root = _normalize_out_root(str(out_root_input.value or "")) if out_root_input is not None else ""
    base = Path(out_root) if out_root else (_PROJECT_ROOT / "out" / "web_gui")
    return base / "template_regions.csv"


def _available_template_names() -> List[str]:
    names = sorted(
        {
            str(row.get("template_name") or "custom_template").strip()
            or "custom_template"
            for row in template_rows
        }
    )
    return names


def _get_active_template_name() -> Optional[str]:
    global active_template_name

    names = _available_template_names()
    if not names:
        active_template_name = None
        return None

    if active_template_name not in names:
        active_template_name = names[0]

    return active_template_name


def _active_template_rows() -> List[Dict[str, Any]]:
    name = _get_active_template_name()
    if not name:
        return []

    return [
        row
        for row in template_rows
        if str(row.get("template_name") or "custom_template").strip() == name
    ]


def _refresh_template_name_select() -> None:
    global active_template_name

    if template_name_select is None:
        return

    names = _available_template_names()
    options = {name: name for name in names}

    template_name_select.options = options

    if names:
        if active_template_name not in names:
            active_template_name = names[0]
        template_name_select.value = active_template_name
    else:
        active_template_name = None
        template_name_select.value = None

    template_name_select.update()


def _template_region_options() -> Dict[str, str]:
    return {
        str(r.get("region_id", "")): (
            f"{r.get('region_id', '')} · "
            f"{r.get('type', '')} · "
            f"source={r.get('content_source', '')}"
        )
        for r in _active_template_rows()
    }


def _selected_template_row() -> Optional[Dict[str, Any]]:
    active_rows = _active_template_rows()

    rid = selected_template_region_id or (
        template_region_select.value if template_region_select is not None else None
    )

    for row in active_rows:
        if str(row.get("region_id")) == str(rid):
            return row

    return active_rows[0] if active_rows else None


def _set_template_status(message: str) -> None:
    if template_status_label is not None:
        template_status_label.text = message


def _template_preview_svg(width: int = 390, height: int = 520) -> str:
    selected_id = selected_template_region_id or (template_region_select.value if template_region_select is not None else "")
    parts = [f'''
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="{width}" height="{height}" rx="22" fill="#111827"/>
      <rect x="22" y="22" width="{width-44}" height="{height-44}" rx="14" fill="#ffffff" stroke="#d1d5db" stroke-width="2"/>
    ''']
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
    for row in _active_template_rows():
        rx = page_x + float(row.get("x", 0)) * page_w
        ry = page_y + float(row.get("y", 0)) * page_h
        rw = float(row.get("w", 0.1)) * page_w
        rh = float(row.get("h", 0.1)) * page_h
        rtype = str(row.get("type", "text_block"))
        fill, stroke = palette.get(rtype, ("#f3f4f6", "#6b7280"))
        selected = str(row.get("region_id")) == str(selected_id)
        sw = 4 if selected else 2
        opacity = 0.92 if selected else 0.62
        dash = "" if rtype in {"table", "field", "header"} else " stroke-dasharray=\"6 5\""
        parts.append(
            f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" rx="7" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"{dash}/>'
        )
        label = str(row.get("label") or row.get("region_id") or "region")[:28]
        parts.append(
            f'<text x="{rx+7:.1f}" y="{ry+18:.1f}" font-size="11" fill="#111827">{label}</text>'
        )
        if rtype == "table":
            cols = int(row.get("cols") or 4) if str(row.get("cols") or "").strip() else 4
            rows_n = int(row.get("max_rows") or 4) if str(row.get("max_rows") or "").strip() else 4
            rows_n = max(2, min(rows_n, 8))
            cols = max(2, min(cols, 8))
            for k in range(1, cols):
                x = rx + k * rw / cols
                parts.append(f'<line x1="{x:.1f}" y1="{ry:.1f}" x2="{x:.1f}" y2="{ry+rh:.1f}" stroke="{stroke}" stroke-width="1" opacity="0.45"/>')
            for k in range(1, rows_n):
                y = ry + k * rh / rows_n
                parts.append(f'<line x1="{rx:.1f}" y1="{y:.1f}" x2="{rx+rw:.1f}" y2="{y:.1f}" stroke="{stroke}" stroke-width="1" opacity="0.45"/>')
    parts.append("</svg>")
    return "".join(parts)


def _refresh_template_region_select() -> None:
    global selected_template_region_id

    if template_region_select is None:
        return

    opts = _template_region_options()
    template_region_select.options = opts

    if opts:
        if selected_template_region_id not in opts:
            selected_template_region_id = next(iter(opts.keys()))
        template_region_select.value = selected_template_region_id
    else:
        selected_template_region_id = None
        template_region_select.value = None

    template_region_select.update()

def _load_selected_template_region_to_editor() -> None:
    row = _selected_template_row()
    if row is None:
        return
    if template_region_type_select is not None:
        template_region_type_select.value = str(row.get("type", "text_block"))
    if template_region_label_input is not None:
        template_region_label_input.value = str(row.get("label", ""))
    if template_region_content_source_input is not None:
        template_region_content_source_input.value = str(row.get("content_source", ""))
    if template_region_x_input is not None:
        template_region_x_input.value = float(row.get("x", 0.0))
    if template_region_y_input is not None:
        template_region_y_input.value = float(row.get("y", 0.0))
    if template_region_w_input is not None:
        template_region_w_input.value = float(row.get("w", 0.1))
    if template_region_h_input is not None:
        template_region_h_input.value = float(row.get("h", 0.1))
    if template_region_min_rows_input is not None:
        template_region_min_rows_input.value = int(row.get("min_rows") or 0)
    if template_region_max_rows_input is not None:
        template_region_max_rows_input.value = int(row.get("max_rows") or 0)
    if template_region_cols_input is not None:
        template_region_cols_input.value = int(row.get("cols") or 0)
    if template_region_required_switch is not None:
        template_region_required_switch.value = bool(row.get("required", False))
    if template_region_jitter_input is not None:
        template_region_jitter_input.value = float(row.get("jitter", 0.01))


def _apply_template_editor_to_selected_region(*_: Any) -> None:
    row = _selected_template_row()
    if row is None:
        return
    row["type"] = str(template_region_type_select.value or "text_block") if template_region_type_select is not None else row.get("type", "text_block")
    row["label"] = str(template_region_label_input.value or row.get("region_id", "region")) if template_region_label_input is not None else row.get("label", "")
    if template_region_content_source_input is not None:
        row["content_source"] = str(template_region_content_source_input.value or "").strip()
    x = _parse_template_float(template_region_x_input.value if template_region_x_input is not None else row.get("x"), 0.0)
    y = _parse_template_float(template_region_y_input.value if template_region_y_input is not None else row.get("y"), 0.0)
    w = _parse_template_float(template_region_w_input.value if template_region_w_input is not None else row.get("w"), 0.1)
    h = _parse_template_float(template_region_h_input.value if template_region_h_input is not None else row.get("h"), 0.1)
    x = max(0.0, min(1.0, x))
    y = max(0.0, min(1.0, y))
    w = max(0.01, min(1.0 - x, w))
    h = max(0.01, min(1.0 - y, h))
    row["x"], row["y"], row["w"], row["h"] = x, y, w, h
    row["min_rows"] = int(template_region_min_rows_input.value or 0) if template_region_min_rows_input is not None else row.get("min_rows", "")
    row["max_rows"] = int(template_region_max_rows_input.value or 0) if template_region_max_rows_input is not None else row.get("max_rows", "")
    row["cols"] = int(template_region_cols_input.value or 0) if template_region_cols_input is not None else row.get("cols", "")
    row["required"] = bool(template_region_required_switch.value) if template_region_required_switch is not None else row.get("required", False)
    row["jitter"] = max(0.0, min(0.20, _parse_template_float(template_region_jitter_input.value if template_region_jitter_input is not None else row.get("jitter"), 0.01)))
    _refresh_template_region_select()
    _update_template_preview()


def _update_template_preview() -> None:
    svg = _template_preview_svg()

    if template_preview_html is not None:
        template_preview_html.set_content(svg)

    if template_editor_preview_html is not None:
        template_editor_preview_html.set_content(svg)

    active_rows = _active_template_rows()
    active_name = _get_active_template_name() or "-"

    _set_template_status(
        f"Templates loaded: {len(_available_template_names())} · "
        f"Active: {active_name} · "
        f"Active regions: {len(active_rows)} · "
        f"Total regions: {len(template_rows)}"
    )


def _on_template_region_selected(e: Any) -> None:
    global selected_template_region_id
    selected_template_region_id = str(e.value or "")
    _load_selected_template_region_to_editor()
    _update_template_preview()

def _on_template_name_selected(e: Any) -> None:
    global active_template_name, selected_template_region_id

    active_template_name = str(e.value or "").strip() or None
    selected_template_region_id = None

    _refresh_template_region_select()
    _load_selected_template_region_to_editor()
    _update_template_preview()


def _load_sample_template_rows() -> None:
    global template_rows, active_template_name, selected_template_region_id

    template_rows = [_coerce_template_row(dict(r)) for r in SAMPLE_TEMPLATE_ROWS]

    names = _available_template_names()
    active_template_name = names[0] if names else None

    active_rows = _active_template_rows()
    selected_template_region_id = (
        str(active_rows[0].get("region_id"))
        if active_rows
        else None
    )

    _refresh_template_name_select()
    _refresh_template_region_select()
    _load_selected_template_region_to_editor()
    _update_template_preview()
    _set_template_status(
        f"Loaded built-in sample templates: "
        f"{len(names)} template(s), {len(template_rows)} region(s)."
    )



def _strip_excel_sep_line(text: str) -> str:
    """Remove Excel delimiter hint line like 'sep=;' before csv.DictReader sees it."""
    lines = str(text or "").splitlines()
    if lines and lines[0].strip().lower().startswith("sep="):
        return "\n".join(lines[1:])
    return str(text or "")

def _make_csv_reader(text: str) -> csv.DictReader:
    """Create a CSV DictReader that supports Excel-style ; CSV and normal comma CSV."""
    clean_text = _strip_excel_sep_line(text)
    sample = clean_text[:4096]

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    except Exception:
        dialect = csv.excel
        dialect.delimiter = CSV_EXPORT_DELIMITER

    return csv.DictReader(io.StringIO(clean_text), dialect=dialect)



async def _read_upload_bytes(e: Any) -> bytes:
    """Read NiceGUI upload payloads safely.

    Fixes cases where e.content.read() returns a coroutine instead of bytes.
    """
    src = getattr(e, "content", None) or getattr(e, "file", None)
    if src is None:
        raise RuntimeError("Upload payload not found")

    if hasattr(src, "read"):
        data = src.read()
        if asyncio.iscoroutine(data):
            data = await data
    else:
        data = src

    if isinstance(data, bytes):
        return data

    if isinstance(data, bytearray):
        return bytes(data)

    if isinstance(data, str):
        return data.encode("utf-8")

    raise RuntimeError(f"Unsupported upload payload type: {type(data).__name__}")




async def _handle_template_csv_upload(e: Any) -> None:
    global template_rows, active_template_name, selected_template_region_id

    try:
        uploaded_bytes = await _read_upload_bytes(e)
        text = uploaded_bytes.decode("utf-8-sig", errors="replace")

        reader = _make_csv_reader(text)
        rows = [_coerce_template_row(dict(r)) for r in reader]

        if not rows:
            ui.notify("Template CSV is empty", color="warning")
            return

        template_rows = rows

        names = _available_template_names()
        active_template_name = names[0] if names else None

        active_rows = _active_template_rows()
        selected_template_region_id = (
            str(active_rows[0].get("region_id"))
            if active_rows
            else None
        )

        _refresh_template_name_select()
        _refresh_template_region_select()
        _load_selected_template_region_to_editor()
        _update_template_preview()



        if document_template_select is not None:
            document_template_select.value = "Custom CSV template"

        ui.notify(f"Template CSV loaded: {len(template_rows)} regions", color="positive")

    except Exception as ex:
        ui.notify(f"Template CSV load failed: {ex}", color="negative")



def _export_template_csv_example() -> None:
    try:
        path = _template_output_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        rows = template_rows if template_rows else [
            _coerce_template_row(dict(r)) for r in SAMPLE_TEMPLATE_ROWS
        ]

        with path.open("w", newline="", encoding="utf-8-sig") as f:
            # Excel hint: forces Excel to split columns with the selected delimiter.
            # This line is ignored by our importer via _strip_excel_sep_line().
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




def _open_template_csv() -> None:
    path = _template_output_path()
    if not path.exists():
        ui.notify("Template CSV not found. Export it first.", color="warning")
        return
    _open_path(str(path))


# ---------------------------------------------------------
# Files / content helpers
# ---------------------------------------------------------

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


def _content_dir() -> Path:
    return _PROJECT_ROOT / "data" / "content"


def _reset_content_csvs() -> None:
    try:
        content_dir = _content_dir()
        reset_content_to_samples(content_dir)
        ui.notify(f"Content CSVs reset: {content_dir}", color="warning")
    except Exception as e:
        ui.notify(f"Content reset failed: {e}", color="negative")


def _ensure_custom_content_csvs() -> None:
    try:
        content_dir = _content_dir()
        ensure_content_bank(orchestrator.build_config_with_user_override(
            config_path=_normalize_config_path(str(config_path_input.value or "")),
            overrides=None,
            raw_yaml_override_text=None,
        ))
        ui.notify(f"Custom content CSVs ready: {content_dir}", color="positive")
    except Exception as e:
        ui.notify(f"Content setup failed: {e}", color="negative")


async def _save_uploaded_content_csv(e: Any, filename: str) -> None:
    try:
        content_dir = _content_dir()
        content_dir.mkdir(parents=True, exist_ok=True)

        target_path = content_dir / filename
        uploaded_bytes = await _read_upload_bytes(e)

        text = uploaded_bytes.decode("utf-8-sig", errors="replace")
        target_path.write_text(text, encoding="utf-8-sig", newline="")

        ensure_content_bank(
            orchestrator.build_config_with_user_override(
                config_path=_normalize_config_path(str(config_path_input.value or "")),
                overrides=None,
                raw_yaml_override_text=None,
            )
        )

        ui.notify(f"{filename} saved to: {target_path}", color="positive")

    except Exception as ex:
        ui.notify(f"{filename} upload failed: {ex}", color="negative")

# ---------------------------------------------------------
# Form events / dynamic schema fields
# ---------------------------------------------------------

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
                w = ui.textarea(label=label, value=initial).classes("w-full").props("rows=4")
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
        with ui.expansion(f"{title_prefix}{group_name}", icon="tune", value=False).classes("w-full"):
            with ui.column().classes("w-full gap-2"):
                for field in fields:
                    _make_field(field, ui.row().classes("w-full"))


# ---------------------------------------------------------
# Status / run actions
# ---------------------------------------------------------

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
        if state_label is not None:
            state_label.text = "idle"
        if run_id_label is not None:
            run_id_label.text = "-"
        return

    try:
        status = orchestrator.get_status(current_run_id)
        summary = orchestrator.get_summary(current_run_id)

        run_id_label.text = current_run_id
        state_label.text = status.state
        pid_label.text = str(status.pid) if status.pid is not None else "-"
        return_code_label.text = str(status.return_code) if status.return_code is not None else "-"
        out_root_label.text = status.out_root or "-"
        progress_label.text = status.progress.state if status.progress else "-"

        if status_json is not None:
            status_json.value = _status_to_text(status)
        if summary_json is not None:
            summary_json.value = _summary_to_text(summary)

        if stdout_log is not None and status.stdout_log:
            stdout_log.value = tail_text(status.stdout_log, 12000)
        if stderr_log is not None and status.stderr_log:
            stderr_log.value = tail_text(status.stderr_log, 12000)

        if status.state in {"done", "failed", "cancelled"}:
            start_btn.enable()
            stop_btn.disable()

    except Exception as e:
        ui.notify(f"Status refresh error: {e}", color="negative")


def _save_advanced_to_user_yaml() -> None:
    try:
        config_path = _normalize_config_path(str(config_path_input.value or ""))
        nested = _nested_from_flat_overrides(_collect_overrides())

        raw_yaml_text = ""
        if raw_yaml_override_input is not None:
            raw_yaml_text = str(raw_yaml_override_input.value or "").strip()

        if raw_yaml_text:
            raw_dict = orchestrator.parse_raw_yaml_override(raw_yaml_text)
            nested = orchestrator.merge_raw_yaml_override(
                nested,
                yaml.safe_dump(raw_dict, sort_keys=False, allow_unicode=True),
            )

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

            overrides = _collect_all_overrides_for_run()

            req = RunRequest(
                config_path=config_path,
                out_root=out_root,
                pages=int(pages_input.value or 0),
                workers=int(workers_input.value or 0),
                seed=int(seed_input.value or -1),
                smoke_test=bool(smoke_test_input.value),
                overrides=overrides,
            )

            current_run_id = orchestrator.start(req)

            run_id_label.text = current_run_id
            state_label.text = "running"
            progress_label.text = "started"

            if stdout_log is not None:
                stdout_log.value = ""
            if stderr_log is not None:
                stderr_log.value = ""
            if status_json is not None:
                status_json.value = ""
            if summary_json is not None:
                summary_json.value = ""

            start_btn.disable()
            stop_btn.enable()

            ui.notify(f"Run started: {current_run_id}", color="positive")

        except Exception as e:
            ui.notify(f"Run start failed: {e}", color="negative")


def _stop_run() -> None:
    global current_run_id

    if not current_run_id:
        return
    ok = orchestrator.cancel(current_run_id)
    if ok:
        state_label.text = "cancelled"
        start_btn.enable()
        stop_btn.disable()
        ui.notify("Run cancelled", color="warning")


def _open_output_folder() -> None:
    if not current_run_id:
        ui.notify("No run yet", color="warning")
        return
    try:
        summary = orchestrator.get_summary(current_run_id)
        if summary.out_root:
            _open_path(summary.out_root)
        else:
            ui.notify("Output folder not available yet", color="warning")
    except Exception as e:
        ui.notify(f"Open output failed: {e}", color="negative")


def _open_qc_summary() -> None:
    if not current_run_id:
        ui.notify("No run yet", color="warning")
        return
    try:
        summary = orchestrator.get_summary(current_run_id)
        if summary.qc_summary_path:
            _open_path(summary.qc_summary_path)
        else:
            ui.notify("qc_summary.json not available yet", color="warning")
    except Exception as e:
        ui.notify(f"Open qc_summary failed: {e}", color="negative")


def _open_run_log() -> None:
    if not current_run_id:
        ui.notify("No run yet", color="warning")
        return
    try:
        summary = orchestrator.get_summary(current_run_id)
        if summary.run_log_path:
            _open_path(summary.run_log_path)
        else:
            ui.notify("run.log not available yet", color="warning")
    except Exception as e:
        ui.notify(f"Open run.log failed: {e}", color="negative")


# ---------------------------------------------------------
# Recipe CSV helpers
# ---------------------------------------------------------

def _recipe_csv_path() -> str:
    config_path = _normalize_config_path(str(config_path_input.value or ""))
    return str(Path(config_path).with_suffix(".recipe.csv"))


def _export_recipe_csv() -> None:
    try:
        rows = []

        rows.append({
            "section": "run",
            "key": "config_path",
            "value": _normalize_config_path(str(config_path_input.value or "")),
        })
        rows.append({
            "section": "run",
            "key": "out_root",
            "value": _normalize_out_root(str(out_root_input.value or "")),
        })
        rows.append({
            "section": "run",
            "key": "pages",
            "value": int(pages_input.value or 0),
        })
        rows.append({
            "section": "run",
            "key": "workers",
            "value": int(workers_input.value or 0),
        })
        rows.append({
            "section": "run",
            "key": "seed",
            "value": int(seed_input.value or -1),
        })
        rows.append({
            "section": "run",
            "key": "smoke_test",
            "value": bool(smoke_test_input.value),
        })

        if dataset_goal_select is not None:
            rows.append({
                "section": "simple",
                "key": "dataset_goal",
                "value": str(dataset_goal_select.value or ""),
            })
            rows.append({
                "section": "simple",
                "key": "dataset_character",
                "value": str(dataset_character_select.value or ""),
            })
            rows.append({
                "section": "simple",
                "key": "content_mix",
                "value": str(content_mix_select.value or ""),
            })
            rows.append({
                "section": "simple",
                "key": "text_length",
                "value": str(text_length_select.value or ""),
            })
            rows.append({
                "section": "simple",
                "key": "table_amount",
                "value": str(table_amount_select.value or ""),
            })
            rows.append({
                "section": "simple",
                "key": "variation",
                "value": str(variation_select.value or ""),
            })
            rows.append({
                "section": "simple",
                "key": "diversity_strength",
                "value": str(diversity_strength_select.value or "") if diversity_strength_select is not None else "",
            })

        for key, widget in field_widgets.items():
            value = _read_widget_value(key, widget)
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)

            rows.append({
                "section": "field",
                "key": key,
                "value": value,
            })

        raw_yaml_text = ""
        if raw_yaml_override_input is not None:
            raw_yaml_text = str(raw_yaml_override_input.value or "").strip()

        if raw_yaml_text:
            rows.append({
                "section": "raw_yaml",
                "key": "raw_yaml_override",
                "value": raw_yaml_text,
            })

        csv_path = _recipe_csv_path()
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            # Excel hint: forces Excel to split columns with the selected delimiter.
            # This line is ignored by our importer via _strip_excel_sep_line().
            f.write(f"sep={CSV_EXPORT_DELIMITER}\n")

            writer = csv.DictWriter(
                f,
                fieldnames=["section", "key", "value"],
                delimiter=CSV_EXPORT_DELIMITER,
            )
            writer.writeheader()
            writer.writerows(rows)

        ui.notify(f"CSV exported: {csv_path}", color="positive")

    except Exception as e:
        ui.notify(f"CSV export failed: {e}", color="negative")


def _open_recipe_csv() -> None:
    try:
        csv_path = _recipe_csv_path()

        if not Path(csv_path).exists():
            ui.notify("Recipe CSV not found. Export it first.", color="warning")
            return

        _open_path(csv_path)

    except Exception as e:
        ui.notify(f"Open Recipe CSV failed: {e}", color="negative")


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

    pending_goal: Optional[str] = None
    pending_character: Optional[str] = None
    pending_content_mix: Optional[str] = None
    pending_text_length: Optional[str] = None
    pending_table_amount: Optional[str] = None
    pending_variation: Optional[str] = None
    pending_diversity_strength: Optional[str] = None

    _csv_loading_mode = True

    try:
        for row in rows:
            section = str(row.get("section", "") or "").strip().lower()
            key = str(row.get("key", "") or "").strip()
            value = row.get("value", "")

            if section == "run":
                if key == "config_path":
                    pending_config_path = _normalize_config_path(str(value or ""))

                elif key == "out_root":
                    pending_out_root = _normalize_out_root(str(value or ""))

                elif key == "pages":
                    try:
                        pending_pages = int(float(value or 0))
                    except Exception:
                        pending_pages = 0

                elif key == "workers":
                    try:
                        pending_workers = int(float(value or 0))
                    except Exception:
                        pending_workers = 0

                elif key == "seed":
                    try:
                        pending_seed = int(float(value or -1))
                    except Exception:
                        pending_seed = -1

                elif key == "smoke_test":
                    pending_smoke_test = str(value).strip().lower() in {
                        "1",
                        "true",
                        "yes",
                        "on",
                        "y",
                    }

            elif section == "simple":
                if key == "dataset_goal":
                    pending_goal = str(value or "")

                elif key == "dataset_character":
                    pending_character = str(value or "")

                elif key == "content_mix":
                    pending_content_mix = str(value or "")

                elif key == "text_length":
                    pending_text_length = str(value or "")

                elif key == "table_amount":
                    pending_table_amount = str(value or "")

                elif key == "variation":
                    pending_variation = str(value or "")

                elif key == "diversity_strength":
                    pending_diversity_strength = str(value or "")

            elif section == "field":
                field = SCHEMA_MAP.get(key, {})
                field_type = field.get("field_type", "str")

                parsed: Any = value

                try:
                    if field_type == "bool":
                        parsed = str(value).strip().lower() in {
                            "1",
                            "true",
                            "yes",
                            "on",
                            "y",
                        }

                    elif field_type == "int":
                        parsed = int(float(value))

                    elif field_type == "float":
                        parsed = float(value)

                    elif field_type in {"json", "color_rgb"}:
                        try:
                            parsed = json.loads(value)
                        except Exception:
                            parsed = value

                    else:
                        parsed = str(value or "")

                except Exception:
                    parsed = value

                override_map[key] = parsed

            elif section == "raw_yaml":
                txt = str(value or "").strip()
                if txt:
                    raw_yaml_parts.append(txt)

        if pending_config_path is not None and config_path_input is not None:
            config_path_input.value = pending_config_path
            _load_baseline_and_user_config()

        if pending_out_root is not None and out_root_input is not None:
            out_root_input.value = pending_out_root

        if pending_pages is not None and pages_input is not None:
            pages_input.value = pending_pages

        if pending_workers is not None and workers_input is not None:
            workers_input.value = pending_workers

        if pending_seed is not None and seed_input is not None:
            seed_input.value = pending_seed

        if pending_smoke_test is not None and smoke_test_input is not None:
            smoke_test_input.value = pending_smoke_test

        if dataset_goal_select is not None:
            if pending_goal in DATASET_GOAL_PRESETS:
                dataset_goal_select.value = pending_goal

            if pending_character in DATASET_CHARACTER_PRESETS:
                dataset_character_select.value = pending_character

            if pending_content_mix in CONTENT_MIX_PRESETS:
                content_mix_select.value = pending_content_mix

            if pending_text_length in TEXT_LENGTH_PRESETS:
                text_length_select.value = pending_text_length

            if pending_table_amount in TABLE_AMOUNT_PRESETS:
                table_amount_select.value = pending_table_amount

            if pending_variation in VARIATION_PRESETS:
                variation_select.value = pending_variation

            if (
                pending_diversity_strength in DIVERSITY_STRENGTH_PRESETS
                and diversity_strength_select is not None
            ):
                diversity_strength_select.value = pending_diversity_strength

        if override_map:
            _load_form_from_override_map(override_map)

        if raw_yaml_override_input is not None:
            raw_yaml_override_input.value = "\n\n".join(raw_yaml_parts).strip()

        _update_preview()
        _refresh_effective_yaml_preview()

    finally:
        _csv_loading_mode = False

        
async def _handle_recipe_csv_upload(e: Any) -> None:
    try:
        uploaded_bytes = await _read_upload_bytes(e)
        text = uploaded_bytes.decode("utf-8-sig", errors="replace")

        reader = _make_csv_reader(text)
        rows = list(reader)

        if not rows:
            ui.notify("CSV is empty", color="warning")
            return

        _apply_recipe_csv_rows(rows)
        ui.notify("CSV loaded into form", color="positive")

    except Exception as ex:
        ui.notify(f"CSV load failed: {ex}", color="negative")

        
# ---------------------------------------------------------
# Page layout
# ---------------------------------------------------------

ui.dark_mode().enable()

with ui.header().classes("items-center justify-between"):
    with ui.row().classes("items-center gap-3"):
        ui.label("AI1 Gen").classes("text-2xl font-bold")
        ui.badge("Synthetic Document AI Dataset Generator", color="blue")
    with ui.row():
        ui.button("Refresh Status", on_click=_refresh_status_panels, icon="refresh")
        ui.button("Open Output", on_click=_open_output_folder, icon="folder_open")

with ui.column().classes("w-full max-w-7xl mx-auto p-4 gap-4"):

    with ui.card().classes("w-full p-5"):
        ui.label("Create a dataset in 3 steps").classes("text-3xl font-bold")
        ui.label(
            "Choose a preset, preview the expected document structure, then generate images, masks, annotations, and ground-truth JSON."
        ).classes("text-base text-gray-400")

    with ui.row().classes("w-full flex-wrap items-start gap-4 overflow-hidden"):

        # LEFT: Friendly setup
        with ui.column().classes("w-full lg:w-[430px] max-w-full gap-4"):

            with ui.card().classes("w-full p-5"):
                ui.label("1. Dataset setup").classes("text-xl font-semibold")

                document_template_select = ui.select(
                    options=list(DOCUMENT_TEMPLATE_PRESETS.keys()),
                    value="Generic random document",
                    label="Document template",
                    on_change=lambda e: _update_preview(),
                ).classes("w-full")
                document_template_select.tooltip("Choose a workflow-oriented document type or use a custom CSV template.")

                dataset_goal_select = ui.select(
                    options=list(DATASET_GOAL_PRESETS.keys()),
                    value="Quick OCR Dataset",
                    label="What do you want to generate?",
                    on_change=lambda e: _update_preview(),
                ).classes("w-full")
                dataset_goal_select.tooltip("Choose the main purpose of the generated dataset.")

                dataset_character_select = ui.select(
                    options=list(DATASET_CHARACTER_PRESETS.keys()),
                    value="Balanced",
                    label="Visual character",
                    on_change=lambda e: _update_preview(),
                ).classes("w-full")
                dataset_character_select.tooltip("Controls how clean, scanned, or noisy the pages should look.")

                content_mix_select = ui.select(
                    options=list(CONTENT_MIX_PRESETS.keys()),
                    value="Mostly Text",
                    label="Content mix",
                    on_change=lambda e: _update_preview(),
                ).classes("w-full")
                content_mix_select.tooltip("Controls whether pages are mostly text, math-heavy, table-heavy, or mixed.")

                with ui.row().classes("w-full gap-2 flex-wrap"):
                    text_length_select = ui.select(
                        options=list(TEXT_LENGTH_PRESETS.keys()),
                        value="Balanced blocks",
                        label="Text block length",
                        on_change=lambda e: _update_preview(),
                    ).classes("w-full md:flex-1")
                    text_length_select.tooltip("Controls whether pages look like short OCR snippets or longer paragraph pages.")

                    table_amount_select = ui.select(
                        options=list(TABLE_AMOUNT_PRESETS.keys()),
                        value="Some tables",
                        label="Table amount",
                        on_change=lambda e: _update_preview(),
                    ).classes("w-full md:flex-1")
                    table_amount_select.tooltip("Controls how often tables should appear.")

                variation_select = ui.select(
                    options=list(VARIATION_PRESETS.keys()),
                    value="Medium",
                    label="Variation",
                    on_change=lambda e: _update_preview(),
                ).classes("w-full")
                variation_select.tooltip("Controls how much layout diversity the dataset should have.")

                diversity_strength_select = ui.select(
                    options=list(DIVERSITY_STRENGTH_PRESETS.keys()),
                    value="Balanced diversity",
                    label="Diversity strength",
                    on_change=lambda e: _update_preview(),
                ).classes("w-full")
                diversity_strength_select.tooltip(
                    "Controls how aggressively the generator diversifies text, tables, LaTeX, layout, noise, density, and scripts."
                )


                simple_summary_label = ui.label("").classes("text-sm text-gray-400")

            with ui.card().classes("w-full p-5"):
                ui.label("2. Run options").classes("text-xl font-semibold")

                config_path_input = ui.input(
                    "Config Path",
                    value=str(_DEFAULT_CONFIG.resolve()),
                ).classes("w-full")
                config_path_input.on_value_change(_on_config_path_change)

                out_root_input = ui.input(
                    "Output Folder",
                    value=str((_PROJECT_ROOT / "out" / "web_gui").resolve()),
                ).classes("w-full")
                out_root_input.on_value_change(_on_any_field_change)

                with ui.row().classes("w-full gap-2"):
                    pages_input = ui.number("Pages", value=100, step=1, min=1).classes("w-1/3")
                    workers_input = ui.number("Workers", value=4, step=1, min=1).classes("w-1/3")
                    seed_input = ui.number("Seed", value=1337, step=1).classes("w-1/3")

                pages_input.on_value_change(_on_any_field_change)
                workers_input.on_value_change(_on_any_field_change)
                seed_input.on_value_change(_on_any_field_change)

                smoke_test_input = ui.switch("Smoke test / quick validation", value=False)
                smoke_test_input.tooltip("Use this when you only want to verify that the pipeline works.")

                with ui.row().classes("w-full gap-3"):
                    start_btn = ui.button(
                        "Generate Dataset",
                        on_click=_start_run,
                        icon="play_arrow",
                    ).classes("flex-1")
                    stop_btn = ui.button(
                        "Stop",
                        on_click=_stop_run,
                        icon="stop",
                    ).classes("flex-1")
                    stop_btn.disable()

        # RIGHT: Preview and simple status
        with ui.column().classes("w-full lg:flex-1 min-w-0 gap-4"):

            with ui.card().classes("w-full p-5"):
                ui.label("3. Preview expected output").classes("text-xl font-semibold")
                ui.label(
                    "This is an approximate structure preview. Final pages will vary by random sampling."
                ).classes("text-sm text-gray-400")

                with ui.row().classes("w-full justify-center"):
                    preview_html = ui.html("").classes("p-2 max-w-full overflow-hidden")

                preview_caption = ui.label("").classes("text-sm text-gray-400")

                with ui.row().classes("gap-2 flex-wrap"):
                    ui.button("Refresh Preview", on_click=_update_preview, icon="visibility")
                    ui.button("Show Effective YAML", on_click=_refresh_effective_yaml_preview, icon="code")

            with ui.card().classes("w-full p-5"):
                ui.label("Custom template preview").classes("text-xl font-semibold")
                ui.label("Upload or edit a CSV template in Power user settings. Region boxes can be adjusted from the GUI.").classes("text-sm text-gray-400")
                with ui.row().classes("w-full justify-center"):
                    template_preview_html = ui.html("").classes("p-2 max-w-full overflow-hidden")

            with ui.card().classes("w-full p-5"):
                ui.label("What will be generated?").classes("text-xl font-semibold")
                ui.label("Output folder structure after a successful run:").classes("text-sm text-gray-400")
                with ui.grid(columns=2).classes("w-full gap-2 text-sm"):
                    ui.label("images/").classes("font-bold")
                    ui.label("Rendered document pages as PNG")
                    ui.label("masks/").classes("font-bold")
                    ui.label("Text and math mask PNG files")
                    ui.label("ann/").classes("font-bold")
                    ui.label("Detailed annotation JSON files")
                    ui.label("gt/").classes("font-bold")
                    ui.label("Ground-truth JSON for training/evaluation")
                    ui.label("splits/").classes("font-bold")
                    ui.label("train / val / test split files")

            with ui.card().classes("w-full p-5"):
                ui.label("Run status").classes("text-xl font-semibold")

                with ui.grid(columns=2).classes("w-full gap-2"):
                    ui.label("State").classes("text-gray-400")
                    state_label = ui.label("idle").classes("font-bold")

                    ui.label("Progress").classes("text-gray-400")
                    progress_label = ui.label("-").classes("font-bold")

                    ui.label("Run ID").classes("text-gray-400")
                    run_id_label = ui.label("-")

                    ui.label("PID").classes("text-gray-400")
                    pid_label = ui.label("-")

                    ui.label("Return code").classes("text-gray-400")
                    return_code_label = ui.label("-")

                    ui.label("Output").classes("text-gray-400")
                    out_root_label = ui.label("-")

                with ui.row().classes("gap-2"):
                    ui.button("Open qc_summary.json", on_click=_open_qc_summary, icon="description")
                    ui.button("Open run.log", on_click=_open_run_log, icon="article")

    # Power user sections
    with ui.expansion("Power user settings", icon="tune", value=False).classes("w-full"):
        with ui.tabs().classes("w-full") as tabs:
            basic_tab = ui.tab("Basic Fields")
            advanced_tab = ui.tab("Advanced YAML")
            recipe_tab = ui.tab("Recipe CSV")
            template_tab = ui.tab("Template CSV")
            content_tab = ui.tab("Content CSVs")
            logs_tab = ui.tab("Logs / JSON")

        with ui.tab_panels(tabs, value=basic_tab).classes("w-full"):

            with ui.tab_panel(basic_tab):
                with ui.card().classes("w-full p-4"):
                    ui.label("Basic parameter fields").classes("text-lg font-semibold")
                    _build_grouped_fields(orchestrator.get_schema_for_ui("basic"))

            with ui.tab_panel(advanced_tab):
                with ui.card().classes("w-full p-4"):
                    ui.label("Advanced Config Manager").classes("text-lg font-semibold")

                    user_yaml_path_label = ui.label("-").classes("text-sm text-gray-500")

                    with ui.row():
                        ui.button("Reload YAML", on_click=_reload_from_yaml_files, icon="refresh")
                        ui.button("Save Advanced", on_click=_save_advanced_to_user_yaml, icon="save")
                        ui.button("Reset Advanced", on_click=_reset_advanced_to_baseline, icon="restore")

                    raw_yaml_override_input = ui.textarea(
                        label="Raw YAML Override",
                        value="",
                    ).classes("w-full").props("rows=10")
                    raw_yaml_override_input.on_value_change(lambda e: _refresh_effective_yaml_preview())

                    effective_yaml_preview = ui.textarea(
                        label="Effective YAML Preview",
                        value="",
                    ).classes("w-full").props("rows=20 readonly")

                _build_grouped_fields(orchestrator.get_schema_for_ui("advanced"))

            with ui.tab_panel(recipe_tab):
                with ui.card().classes("w-full p-4"):
                    ui.label("CSV Recipe").classes("text-lg font-semibold")
                    ui.label(
                        "Export the current setup as CSV, edit it outside the app, or load it again later."
                    ).classes("text-sm text-gray-400")

                    with ui.row():
                        ui.button("Export Recipe CSV", on_click=_export_recipe_csv, icon="download")
                        ui.button("Open Recipe CSV", on_click=_open_recipe_csv, icon="table_view")

                    csv_upload_widget = ui.upload(
                        on_upload=_handle_recipe_csv_upload,
                        auto_upload=True,
                    ).props("accept=.csv").classes("w-full")

            with ui.tab_panel(template_tab):
                with ui.card().classes("w-full p-4"):
                    ui.label("Custom Template CSV Editor").classes("text-lg font-semibold")
                    ui.label(
                        "Define document regions with CSV, then fine-tune x/y/w/h and table parameters from the GUI. This is a UI-level template editor; renderer integration can be connected later."
                    ).classes("text-sm text-gray-400")

                    with ui.row().classes("gap-2 flex-wrap"):
                        ui.button("Load Sample Template", on_click=_load_sample_template_rows, icon="article")
                        ui.button("Export / Save Template CSV", on_click=_export_template_csv_example, icon="download")
                        ui.button("Open Template CSV", on_click=_open_template_csv, icon="table_view")

                    template_csv_upload_widget = ui.upload(
                        label="Upload template_regions.csv",
                        on_upload=_handle_template_csv_upload,
                        auto_upload=True,
                    ).props("accept=.csv").classes("w-full")

                    template_status_label = ui.label("No template loaded yet.").classes("text-sm text-gray-400")

                    with ui.card().classes("w-full lg:w-[420px] p-4"):
                        ui.label("Region editor").classes("text-lg font-semibold")

                        template_name_select = ui.select(
                            options={},
                            value=None,
                            label="Active Template",
                            on_change=_on_template_name_selected,
                        ).classes("w-full")
                        template_name_select.tooltip(
                            "Select which template_name from the uploaded CSV should be previewed and edited."
                        )

                        template_region_select = ui.select(
                            options={},
                            value=None,
                            label="Selected part / region ID",
                            on_change=_on_template_region_selected,
                        ).classes("w-full")
                        template_region_select.tooltip(
                            "region_id is the stable part ID. It connects the template region to its label, content_source, masks, and annotations."
                        )


                        template_region_type_select = ui.select(
                            options=TEMPLATE_REGION_TYPES,
                            value="text_block",
                            label="Type",
                            on_change=_apply_template_editor_to_selected_region,
                        ).classes("w-full")

                        template_region_label_input = ui.input(
                            "Label",
                            value="",
                        ).classes("w-full")
                        template_region_label_input.tooltip("Human-readable label for this part. Example: seller_info, items_table, signature_area.")
                        template_region_label_input.on_value_change(_apply_template_editor_to_selected_region)

                        template_region_content_source_input = ui.input(
                            "Content source ID",
                            value="",
                        ).classes("w-full")
                        template_region_content_source_input.tooltip("Connects this part to content CSV/content bank entries. Example: company_info, product_rows, invoice_numbers.")
                        template_region_content_source_input.on_value_change(_apply_template_editor_to_selected_region)

                        with ui.grid(columns=2).classes("w-full gap-2"):
                            template_region_x_input = ui.number("Left x", value=0.05, min=0.0, max=1.0, step=0.005, format="%.3f")
                            template_region_y_input = ui.number("Top y", value=0.05, min=0.0, max=1.0, step=0.005, format="%.3f")
                            template_region_w_input = ui.number("Width w", value=0.30, min=0.01, max=1.0, step=0.005, format="%.3f")
                            template_region_h_input = ui.number("Height h", value=0.08, min=0.01, max=1.0, step=0.005, format="%.3f")

                        for w in [template_region_x_input, template_region_y_input, template_region_w_input, template_region_h_input]:
                            w.on_value_change(_apply_template_editor_to_selected_region)

                        with ui.grid(columns=3).classes("w-full gap-2"):
                            template_region_min_rows_input = ui.number("Min rows", value=0, min=0, max=100, step=1)
                            template_region_max_rows_input = ui.number("Max rows", value=0, min=0, max=100, step=1)
                            template_region_cols_input = ui.number("Cols", value=0, min=0, max=50, step=1)

                        for w in [template_region_min_rows_input, template_region_max_rows_input, template_region_cols_input]:
                            w.on_value_change(_apply_template_editor_to_selected_region)

                        template_region_required_switch = ui.switch("Required region", value=True)
                        template_region_required_switch.on_value_change(_apply_template_editor_to_selected_region)

                        template_region_jitter_input = ui.number("Jitter", value=0.01, min=0.0, max=0.20, step=0.005, format="%.3f").classes("w-full")
                        template_region_jitter_input.on_value_change(_apply_template_editor_to_selected_region)

                    with ui.card().classes("w-full lg:flex-1 min-w-0 p-4"):
                        ui.label("Template layout preview").classes("text-lg font-semibold")
                        ui.label("The selected part/region is highlighted. region_id is the stable ID; content_source connects it to content CSVs. Coordinates are normalized between 0 and 1.").classes("text-sm text-gray-400")
                        with ui.row().classes("w-full justify-center"):
                            template_editor_preview_html = ui.html("").classes("p-2 max-w-full overflow-hidden")
                        ui.label("Tip: x + w and y + h must stay within 1.0.").classes("text-sm text-gray-400")

            with ui.tab_panel(content_tab):
                with ui.card().classes("w-full p-4"):
                    ui.label("Content CSVs").classes("text-lg font-semibold")

                    content_source_mode_select = ui.select(
                        options={
                            "content_bank": "Use CSV / Content Bank",
                            "random_chars": "Ignore CSV / Random Characters",
                        },
                        value="content_bank",
                        label="Content Source Mode",
                    ).classes("w-full")

                    with ui.row():
                        ui.button(
                            "Export Content CSV Template",
                            on_click=_reset_content_csvs,
                            icon="table_view",
                        )
                        ui.button(
                            "Build Content Bank JSON",
                            on_click=_ensure_custom_content_csvs,
                            icon="edit_note",
                        )

                    ui.label("Upload custom content CSVs").classes("text-sm text-gray-400")

                    ui.upload(
                        label="Upload words.csv",
                        on_upload=lambda e: asyncio.create_task(_save_uploaded_content_csv(e, "words.csv")),
                        auto_upload=True,
                    ).props("accept=.csv").classes("w-full")

                    ui.upload(
                        label="Upload sentences.csv",
                        on_upload=lambda e: asyncio.create_task(_save_uploaded_content_csv(e, "sentences.csv")),
                        auto_upload=True,
                    ).props("accept=.csv").classes("w-full")

                    ui.upload(
                        label="Upload label_registry.csv",
                        on_upload=lambda e: asyncio.create_task(_save_uploaded_content_csv(e, "label_registry.csv")),
                        auto_upload=True,
                    ).props("accept=.csv").classes("w-full")

            with ui.tab_panel(logs_tab):
                with ui.card().classes("w-full p-4"):
                    ui.label("Outputs / Summary").classes("text-lg font-semibold")
                    summary_json = ui.codemirror(
                        value="",
                        language="JSON",
                    ).classes("w-full").style("height: 260px")

                with ui.card().classes("w-full p-4"):
                    ui.label("Status JSON").classes("text-lg font-semibold")
                    status_json = ui.codemirror(
                        value="",
                        language="JSON",
                    ).classes("w-full").style("height: 220px")

                with ui.card().classes("w-full p-4"):
                    ui.label("stdout").classes("text-lg font-semibold")
                    stdout_log = ui.codemirror(
                        value="",
                        language="text",
                    ).classes("w-full").style("height: 220px")

                with ui.card().classes("w-full p-4"):
                    ui.label("stderr").classes("text-lg font-semibold")
                    stderr_log = ui.codemirror(
                        value="",
                        language="text",
                    ).classes("w-full").style("height: 220px")


_load_baseline_and_user_config()
_load_sample_template_rows()
_update_preview()
ui.timer(1.5, _refresh_status_panels)


def main() -> None:
    ui.run(
        title="AI1 Gen Web GUI",
        host="0.0.0.0",
        port=8080,
        reload=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
