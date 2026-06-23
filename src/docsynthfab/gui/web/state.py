# src/docsynthfab/gui/web/state.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from docsynthfab.orchestrator import RunOrchestrator


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
    # Main generator simple controls
    # ---------------------------------------------------------

    dataset_goal_select: Any = None
    dataset_character_select: Any = None

    # Main generator is text/table only.
    # LaTeX is handled by the dedicated LaTeX page.
    content_mix_preset_select: Any = None
    custom_content_mix_panel: Any = None

    text_mix_input: Any = None
    table_mix_input: Any = None
    content_mix_total_label: Any = None

    font_size_profile_select: Any = None
    font_min_px_input: Any = None
    font_max_px_input: Any = None

    density_percent_input: Any = None
    layout_randomness_percent_input: Any = None
    negative_space_profile_select: Any = None


    # ---------------------------------------------------------
    # User-controlled text / table length controls
    # ---------------------------------------------------------

    text_min_words_input: Any = None
    text_max_words_input: Any = None

    sentence_min_input: Any = None
    sentence_max_input: Any = None

    table_min_rows_input: Any = None
    table_max_rows_input: Any = None
    table_min_cols_input: Any = None
    table_max_cols_input: Any = None
    
    # ---------------------------------------------------------
    # Advanced dataset controls
    # ---------------------------------------------------------

    text_length_select: Any = None
    diversity_strength_select: Any = None
    content_source_mode_select: Any = None

    # Advanced layout / whitespace controls
    whitespace_strategy_select: Any = None
    spread_percent_input: Any = None
    block_gap_percent_input: Any = None
    placement_search_percent_input: Any = None

    # Advanced line-gap distribution controls
    line_gap_distribution_select: Any = None
    line_gap_randomness_percent_input: Any = None
    line_gap_min_scale_input: Any = None
    line_gap_max_scale_input: Any = None
    line_gap_mean_ratio_input: Any = None
    line_gap_std_ratio_input: Any = None
    line_gap_exponential_lambda_input: Any = None

    # ---------------------------------------------------------
    # Dedicated LaTeX renderer / generation page controls
    # ---------------------------------------------------------

    latex_render_enable_switch: Any = None
    latex_missing_behavior_select: Any = None
    latex_http_base_url_input: Any = None
    latex_status_label: Any = None

    latex_text_mix_input: Any = None
    latex_table_mix_input: Any = None
    latex_latex_mix_input: Any = None
    latex_generation_total_label: Any = None

    latex_setup_status_label: Any = None
    latex_setup_commands_label: Any = None

    # ---------------------------------------------------------
    # Fonts status controls
    # ---------------------------------------------------------

    fonts_root_label: Any = None
    fonts_status_label: Any = None
    fonts_manifest_status_label: Any = None
    fonts_license_status_label: Any = None
    fonts_missing_label: Any = None

    fonts_check_button: Any = None
    fonts_open_button: Any = None

    # ---------------------------------------------------------
    # Preview / summary widgets
    # ---------------------------------------------------------

    preview_html: Any = None
    preview_caption: Any = None
    simple_summary_label: Any = None


WEB_STATE = WebGuiState()



