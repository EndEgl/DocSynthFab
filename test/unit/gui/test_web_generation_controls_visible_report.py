from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pytest

from docsynthfab.content.text_provider import TextProvider
from docsynthfab.gui.web.simple_controls import collect_simple_overrides
from docsynthfab.gui.web.state import WebGuiState


class DummyWidget:
    def __init__(self, value: Any = None, text: str = "") -> None:
        self.value = value
        self.text = text
        self.disabled = False

    def enable(self) -> None:
        self.disabled = False

    def disable(self) -> None:
        self.disabled = True

    def update(self) -> None:
        pass

    def set_content(self, value: Any) -> None:
        self.value = value
        self.text = str(value)


def make_visible_state() -> WebGuiState:
    state = WebGuiState()

    # Main dataset controls
    state.dataset_goal_select = DummyWidget("Quick OCR Dataset")
    state.dataset_character_select = DummyWidget("Balanced")
    state.text_length_select = DummyWidget("Balanced blocks")
    state.diversity_strength_select = DummyWidget("Balanced diversity")
    state.document_template_select = DummyWidget("Generic random document")

    # Content mix: main generator text/table only; LaTeX dedicated tabda.
    state.content_mix_preset_select = DummyWidget("Custom")
    state.text_mix_input = DummyWidget(100)
    state.table_mix_input = DummyWidget(0)

    # Word bank mode
    state.content_source_mode_select = DummyWidget("word_bank")

    # Text length controls
    state.text_min_words_input = DummyWidget(3)
    state.text_max_words_input = DummyWidget(3)
    state.sentence_min_input = DummyWidget(2)
    state.sentence_max_input = DummyWidget(4)

    # Table controls
    state.table_min_rows_input = DummyWidget(2)
    state.table_max_rows_input = DummyWidget(5)
    state.table_min_cols_input = DummyWidget(2)
    state.table_max_cols_input = DummyWidget(4)

    # Density and whitespace controls
    state.density_percent_input = DummyWidget(90)

    # 75 -> spread bekliyoruz.
    state.layout_randomness_percent_input = DummyWidget(75)

    # Font controls
    state.font_size_profile_select = DummyWidget("Balanced")
    state.font_min_px_input = DummyWidget(10)
    state.font_max_px_input = DummyWidget(18)

    return state


def write_report(report: dict[str, Any]) -> None:
    root = Path("test_artifacts")
    root.mkdir(parents=True, exist_ok=True)

    json_path = root / "gui_generation_controls_visible_report.json"
    md_path = root / "gui_generation_controls_visible_report.md"

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# GUI Generation Controls Visible Report",
        "",
        "## GUI -> backend overrides",
        "",
        "```json",
        json.dumps(report["overrides"], ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## Word bank samples",
        "",
    ]

    for i, sample in enumerate(report["word_bank_samples"], start=1):
        lines.append(f"{i}. `{sample}`")

    lines += [
        "",
        "## Key interpretation",
        "",
        f"- Content source mode: `{report['content_source_mode']}`",
        f"- Text mode: `{report['text_mode']}`",
        f"- Density distribution: `{report['density_dist']}`",
        f"- Whitespace strategy: `{report['whitespace_strategy']}`",
        f"- Min gap px: `{report['min_gap_px']}`",
        f"- Max place attempts: `{report['max_place_attempts']}`",
        f"- Word count per generated text: `{report['word_count_per_sample']}`",
        "",
    ]

    md_path.write_text("\n".join(lines), encoding="utf-8")


def test_gui_density_word_bank_and_whitespace_are_visible_in_report():
    state = make_visible_state()

    overrides = collect_simple_overrides(state)

    # GUI mode -> backend stable keys.
    assert overrides["content.source_mode"] == "content_bank"
    assert overrides["content.text_mode"] == "words"

    # Main generator does not expose LaTeX mix.
    assert overrides["content.block_mix"]["text"] == 100.0
    assert overrides["content.block_mix"]["table"] == 0.0
    assert overrides["content.block_mix"]["latex"] == 0.0

    # Word count controls.
    assert overrides["content.words"]["min_words"] == 3
    assert overrides["content.words"]["max_words"] == 3

    # Density slider should reach backend density distribution.
    density_dist = overrides["dist.density_dist"]
    assert set(density_dist) == {"sparse", "normal", "dense", "mixed"}
    assert density_dist["dense"] > density_dist["sparse"]

    # Negative-space profile controls whitespace/occupancy.
    # Layout randomness now controls line-gap variation separately.
    occupancy = {
        "whitespace_strategy": overrides["layout.occupancy.whitespace_strategy"],
        "min_gap_px": overrides["layout.occupancy.min_gap_px"],
        "max_place_attempts": overrides["layout.occupancy.max_place_attempts"],
        "target_fill_ratio": overrides["layout.occupancy.target_fill_ratio"],
    }

    assert occupancy["whitespace_strategy"] == "balanced"
    assert occupancy["min_gap_px"] > 0
    assert occupancy["max_place_attempts"] > 0
    assert occupancy["target_fill_ratio"]

    assert overrides["content.hard_negative_page_prob"] == 0.0
    assert "layout.targets" in overrides
    assert "qc.visual_coverage.min_content_ratio_by_density" in overrides

    # Small deterministic word bank.
    bank = {
        "version": "content-bank-v1",
        "words": [
            {
                "text": "alpha",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 1.0,
            },
            {
                "text": "beta",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 1.0,
            },
            {
                "text": "gamma",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 1.0,
            },
            {
                "text": "delta",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 1.0,
            },
        ],
        "sentences": [
            {
                "text": "Alpha beta gamma.",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 1.0,
            }
        ],
    }

    provider_cfg = {
        "source_mode": "content_bank",
        "text_mode": "words",
        "words": overrides["content.words"],
        "chars": {"charset": "ab", "min_len": 4, "max_len": 4},
    }

    provider = TextProvider(bank, provider_cfg, random.Random(123))

    samples = [provider.next_text() for _ in range(5)]

    for sample in samples:
        words = sample.split()
        assert len(words) == 3
        assert all(word in {"alpha", "beta", "gamma", "delta"} for word in words)

    report = {
        "overrides": overrides,
        "content_source_mode": overrides["content.source_mode"],
        "text_mode": overrides["content.text_mode"],
        "density_dist": density_dist,
        "whitespace_strategy": occupancy["whitespace_strategy"],
        "min_gap_px": occupancy["min_gap_px"],
        "max_place_attempts": occupancy["max_place_attempts"],
        "word_count_per_sample": 3,
        "word_bank_samples": samples,
    }

    write_report(report)

    print("\n\n=== GUI GENERATION CONTROLS VISIBLE REPORT ===")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print("=== END GUI GENERATION CONTROLS VISIBLE REPORT ===\n")