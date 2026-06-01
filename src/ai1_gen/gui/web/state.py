# src/ai1_gen/gui/web/state.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ai1_gen.orchestrator import RunOrchestrator


@dataclass
class WebGuiState:
    """Mutable state holder for the NiceGUI web app."""

    orchestrator: RunOrchestrator = field(default_factory=RunOrchestrator)

    current_run_id: Optional[str] = None
    last_unknown_run_id: Optional[str] = None
    last_status_log_signature: Optional[str] = None

    field_widgets: Dict[str, Any] = field(default_factory=dict)
    run_lock: threading.Lock = field(default_factory=threading.Lock)

    baseline_overrides: Dict[str, Any] = field(default_factory=dict)
    csv_loading_mode: bool = False

    # ---------------------------------------------------------
    # Config / YAML preview
    # ---------------------------------------------------------

    raw_yaml_override_input: Any = None
    effective_yaml_preview: Any = None
    user_yaml_path_label: Any = None

    # ---------------------------------------------------------
    # Runtime inputs
    # ---------------------------------------------------------

    config_path_input: Any = None
    out_root_input: Any = None
    pages_input: Any = None
    workers_input: Any = None
    seed_input: Any = None
    smoke_test_input: Any = None

    start_btn: Any = None
    stop_btn: Any = None

    # ---------------------------------------------------------
    # Run monitor widgets
    # ---------------------------------------------------------

    run_id_label: Any = None
    state_label: Any = None
    pid_label: Any = None
    return_code_label: Any = None
    out_root_label: Any = None
    progress_label: Any = None

    summary_json: Any = None
    status_json: Any = None
    stdout_log: Any = None
    stderr_log: Any = None

    live_event_log: Any = None
    live_event_status_label: Any = None

    # ---------------------------------------------------------
    # Template / content editor widgets
    # ---------------------------------------------------------

    template_csv_upload_widget: Any = None
    document_template_select: Any = None
    template_name_select: Any = None
    template_region_select: Any = None
    template_preview_html: Any = None
    template_editor_preview_html: Any = None

    template_region_type_select: Any = None
    template_region_label_input: Any = None
    template_region_content_source_input: Any = None
    template_region_x_input: Any = None
    template_region_y_input: Any = None
    template_region_w_input: Any = None
    template_region_h_input: Any = None
    template_region_min_rows_input: Any = None
    template_region_max_rows_input: Any = None
    template_region_cols_input: Any = None
    template_region_required_switch: Any = None
    template_region_jitter_input: Any = None
    template_status_label: Any = None

    template_rows: List[Dict[str, Any]] = field(default_factory=list)
    active_template_name: Optional[str] = None
    selected_template_region_id: Optional[str] = None

    # ---------------------------------------------------------
    # Simple dataset controls
    # ---------------------------------------------------------

    dataset_goal_select: Any = None
    dataset_character_select: Any = None

    # New simple content preset:
    # Example values:
    # - Karışık belge
    # - Metin ağırlıklı
    # - Tablo ağırlıklı
    # - Sadece metin
    # - Sadece tablo
    # - Sadece LaTeX
    # - Özel
    content_mix_preset_select: Any = None

    # Optional panel/container used to show custom Text/Table/LaTeX inputs
    # only when content_mix_preset_select == "Özel".
    custom_content_mix_panel: Any = None

    # Custom content mix values.
    # These stay available, but should normally be hidden under advanced/custom mode.
    text_mix_input: Any = None
    table_mix_input: Any = None
    latex_mix_input: Any = None
    content_mix_total_label: Any = None

    # ---------------------------------------------------------
    # Advanced dataset controls
    # ---------------------------------------------------------

    text_length_select: Any = None
    diversity_strength_select: Any = None
    content_source_mode_select: Any = None

    density_percent_input: Any = None
    line_gap_tolerance_input: Any = None

    whitespace_strategy_select: Any = None
    spread_percent_input: Any = None
    block_gap_percent_input: Any = None
    placement_search_percent_input: Any = None

    # ---------------------------------------------------------
    # Advanced LaTeX renderer controls
    # ---------------------------------------------------------

    latex_render_enable_switch: Any = None
    latex_missing_behavior_select: Any = None
    latex_http_base_url_input: Any = None
    latex_status_label: Any = None

    # ---------------------------------------------------------
    # Preview / summary widgets
    # ---------------------------------------------------------

    preview_html: Any = None
    preview_caption: Any = None
    simple_summary_label: Any = None


WEB_STATE = WebGuiState()