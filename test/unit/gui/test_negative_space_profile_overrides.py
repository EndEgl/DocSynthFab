from __future__ import annotations

from typing import Any

from docsynthfab.gui.web.simple_controls import collect_simple_overrides
from docsynthfab.gui.web.state import WebGuiState


class DummyWidget:
    def __init__(self, value: Any = None) -> None:
        self.value = value


def make_state(profile: str = "Controlled") -> WebGuiState:
    state = WebGuiState()

    state.dataset_goal_select = DummyWidget("Quick OCR Dataset")
    state.dataset_character_select = DummyWidget("Balanced")
    state.text_length_select = DummyWidget("Balanced blocks")
    state.diversity_strength_select = DummyWidget("Balanced diversity")
    state.document_template_select = DummyWidget("Generic random document")

    state.content_mix_preset_select = DummyWidget("Mixed document")
    state.text_mix_input = DummyWidget(70)
    state.table_mix_input = DummyWidget(30)

    state.content_source_mode_select = DummyWidget("word_bank")
    state.text_min_words_input = DummyWidget(18)
    state.text_max_words_input = DummyWidget(32)
    state.sentence_min_input = DummyWidget(2)
    state.sentence_max_input = DummyWidget(4)

    state.table_min_rows_input = DummyWidget(2)
    state.table_max_rows_input = DummyWidget(5)
    state.table_min_cols_input = DummyWidget(2)
    state.table_max_cols_input = DummyWidget(4)

    state.density_percent_input = DummyWidget(75)
    state.layout_randomness_percent_input = DummyWidget(35)
    state.negative_space_profile_select = DummyWidget(profile)

    state.font_size_profile_select = DummyWidget("Balanced")
    state.font_min_px_input = DummyWidget(10)
    state.font_max_px_input = DummyWidget(18)

    return state


def test_controlled_negative_space_reaches_layout_and_qc_overrides():
    overrides = collect_simple_overrides(make_state("Controlled"))

    assert overrides["content.hard_negative_page_prob"] == 0.0

    assert overrides["layout.occupancy.enable"] is True
    assert overrides["layout.occupancy.whitespace_strategy"] == "balanced"
    assert overrides["layout.occupancy.target_fill_ratio"]

    assert "layout.targets" in overrides
    assert overrides["layout.targets"]["normal"]["line_count_range"][0] >= 30
    assert overrides["layout.targets"]["normal"]["block_count_range"][0] >= 7

    assert overrides["qc.visual_coverage.enable"] is True
    assert "qc.visual_coverage.min_content_ratio_by_density" in overrides
    assert "qc.visual_coverage.min_bbox_extent_ratio_by_density" in overrides
    assert overrides["qc.max_block_overlap_ratio_min_area"] <= 0.28

    density = overrides["dist.density_dist"]
    assert density["sparse"] <= 0.08


def test_dense_controlled_is_stricter_than_airy():
    airy = collect_simple_overrides(make_state("Airy"))
    dense = collect_simple_overrides(make_state("Dense controlled"))

    airy_fill = airy["layout.occupancy.target_fill_ratio"]
    dense_fill = dense["layout.occupancy.target_fill_ratio"]

    assert dense_fill["normal"][0] > airy_fill["normal"][0]
    assert dense_fill["dense"][0] > airy_fill["dense"][0]

    assert dense["layout.occupancy.whitespace_strategy"] == "compact"
    assert dense["qc.max_block_overlap_ratio_min_area"] < airy["qc.max_block_overlap_ratio_min_area"]
    assert dense["dist.density_dist"]["sparse"] <= airy["dist.density_dist"]["sparse"]