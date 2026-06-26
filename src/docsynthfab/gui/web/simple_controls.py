# src/docsynthfab/gui/web/simple_controls.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - nicegui>=2.0,<3.0

from __future__ import annotations

from typing import Any, Dict

from docsynthfab.gui.shared.override_utils import (
    clamp_percent,
    density_percent_to_dist,
    font_size_profile_to_range,
    layout_randomness_percent_to_line_gap,
    layout_randomness_percent_to_occupancy,
    merge_maps,
    negative_space_profile_to_density_dist,
    negative_space_profile_to_layout_targets,
    negative_space_profile_to_occupancy,
    negative_space_profile_to_qc_overrides,
    normalize_text_table_mix,
    spacing_percent_to_line_gap_scale,
)

from docsynthfab.gui.web.presets import (
    DATASET_CHARACTER_PRESETS,
    DATASET_GOAL_PRESETS,
    DIVERSITY_STRENGTH_PRESETS,
    DOCUMENT_TEMPLATE_PRESETS,
    TEXT_LENGTH_PRESETS,
)
from docsynthfab.gui.web.state import WebGuiState


CONTENT_MIX_PRESETS: Dict[str, Dict[str, float] | None] = {
    "Mixed document": {"text": 78.0, "table": 22.0},
    "Text-heavy": {"text": 92.0, "table": 8.0},
    "Table-heavy": {"text": 38.0, "table": 62.0},
    "Text only": {"text": 100.0, "table": 0.0},
    "Table only": {"text": 0.0, "table": 100.0},
    "Custom": None,
}

def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _as_int_clamped(value: Any, default: int, low: int, high: int) -> int:
    try:
        x = int(value)
    except Exception:
        x = int(default)

    return max(int(low), min(int(high), x))


def _ordered_pair(a: int, b: int) -> tuple[int, int]:
    a = int(a)
    b = int(b)

    if b < a:
        return b, a

    return a, b

def _widget_value(widget: Any, default: Any) -> Any:
    if widget is None:
        return default

    try:
        value = widget.value
    except Exception:
        return default

    if value is None:
        return default

    return value


def current_content_mix(state: WebGuiState) -> Dict[str, float]:
    preset_name = (
        str(_widget_value(state.content_mix_preset_select, "Mixed document"))
        if state.content_mix_preset_select is not None
        else "Mixed document"
    )

    preset = CONTENT_MIX_PRESETS.get(preset_name)

    if preset is not None:
        return normalize_text_table_mix(
            preset.get("text", 0.0),
            preset.get("table", 0.0),
        )

    return normalize_text_table_mix(
        _widget_value(state.text_mix_input, 70),
        _widget_value(state.table_mix_input, 30),
    )


def content_mix_label(state: WebGuiState) -> str:
    preset_name = (
        str(_widget_value(state.content_mix_preset_select, "Mixed document"))
        if state.content_mix_preset_select is not None
        else "Mixed document"
    )

    raw_total = 0.0

    for widget in (state.text_mix_input, state.table_mix_input):
        if widget is not None:
            raw_total += _as_float(widget.value, 0.0)

    mix = current_content_mix(state)

    if preset_name != "Custom":
        return (
            f"Content mix: Text {mix['text']:.0f}%, "
            f"Table {mix['table']:.0f}%"
        )

    return (
        f"Raw total: {raw_total:.0f} -> normalized: "
        f"Text {mix['text']:.0f}%, Table {mix['table']:.0f}%"
    )


def sync_custom_mix_visibility(state: WebGuiState) -> None:
    if state.custom_content_mix_panel is None or state.content_mix_preset_select is None:
        return

    is_custom = str(state.content_mix_preset_select.value or "") == "Custom"

    try:
        state.custom_content_mix_panel.visible = is_custom
        state.custom_content_mix_panel.update()
    except Exception:
        pass


def _natural_multilingual_alphabet_mix() -> Dict[str, int]:
    """
    Full multilingual public-alpha mix.

    All supported language families stay enabled, but line rendering must keep
    each OCR line script-consistent. Multilingual diversity should happen across
    lines/pages, not as script soup inside one line.
    """
    return {
        "latin_tr": 22,
        "latin_en": 20,
        "latin_de": 14,
        "latin_es": 9,
        "latin_fr": 9,
        "cyrillic_ru": 8,
        "arabic_ar": 7,
        "greek_el": 6,
        "hebrew_he": 5,
        "devanagari_hi": 5,
        "han_zh": 5,
        "kana_ja": 4,
        "hangul_ko": 4,
        "thai_th": 3,
    }


def _scripts_dist_from_alphabet_mix(alphabet_mix: Dict[str, int]) -> Dict[str, float]:
    """
    Derive render.text.scripts_dist from content.word_bank_policy.alphabet_mix.

    This keeps content language/alphabet choices and rendering script choices aligned.
    """
    script_map = {
        "latin_tr": "tr",
        "latin_en": "latin",
        "latin_de": "de",
        "latin_es": "latin",
        "latin_fr": "latin",
        "cyrillic_ru": "ru",
        "arabic_ar": "ar",
        "greek_el": "el",
        "hebrew_he": "he",
        "devanagari_hi": "hi",
        "han_zh": "zh",
        "kana_ja": "ja",
        "hangul_ko": "ko",
        "thai_th": "th",
    }

    out = {
        "latin": 0.0,
        "tr": 0.0,
        "de": 0.0,
        "ru": 0.0,
        "ar": 0.0,
        "el": 0.0,
        "he": 0.0,
        "hi": 0.0,
        "zh": 0.0,
        "ja": 0.0,
        "ko": 0.0,
        "th": 0.0,
        "symbols": 0.0,
    }

    for alphabet, weight in alphabet_mix.items():
        script = script_map.get(str(alphabet).strip().lower())
        if not script:
            continue
        try:
            w = max(0.0, float(weight))
        except Exception:
            w = 0.0
        out[script] = out.get(script, 0.0) + w

    total = sum(v for k, v in out.items() if k != "symbols")

    if total <= 0:
        return {
            "latin": 0.28,
            "tr": 0.14,
            "de": 0.10,
            "ru": 0.08,
            "ar": 0.07,
            "el": 0.06,
            "he": 0.05,
            "hi": 0.05,
            "zh": 0.05,
            "ja": 0.04,
            "ko": 0.04,
            "th": 0.03,
            "symbols": 0.0,
        }

    return {
        key: round(value / total, 4) if key != "symbols" else 0.0
        for key, value in out.items()
    }


def _density_conditioned_noise_dist(density_percent: Any) -> Dict[str, float]:
    """
    Noise should not be independent from density.

    Dense pages usually have smaller text / more content, so heavy noise should be reduced.
    Sparse pages can tolerate heavier noise.
    """
    p = clamp_percent(density_percent, 50.0)

    if p >= 80:
        return {"clean": 0.70, "medium": 0.28, "heavy": 0.02}

    if p >= 60:
        return {"clean": 0.60, "medium": 0.35, "heavy": 0.05}

    if p >= 35:
        return {"clean": 0.50, "medium": 0.40, "heavy": 0.10}

    return {"clean": 0.42, "medium": 0.42, "heavy": 0.16}


def _density_conditioned_font_size_overrides(
    state: WebGuiState,
    density_percent: Any,
) -> Dict[str, Any]:
    """
    Global approximation of density-conditioned font size.

    Full per-page conditional font sampling belongs in renderer/layout backend.
    This GUI-level version is safe and immediately useful:
    - dense -> smaller font range
    - sparse -> larger font range
    """
    profile = str(_widget_value(state.font_size_profile_select, "Balanced"))

    # Respect explicit custom font settings.
    if profile == "Custom":
        min_px = int(_as_float(_widget_value(state.font_min_px_input, 10), 10))
        max_px = int(_as_float(_widget_value(state.font_max_px_input, 18), 18))
        if min_px > max_px:
            min_px, max_px = max_px, min_px
        return {
            "render.text.font_size.min_px": min_px,
            "render.text.font_size.max_px": max_px,
            "render.text.font_size.distribution": "gaussian",
            "render.text.font_size.mean_ratio": 0.68,
            "render.text.font_size.std_ratio": 0.18,
        }

    p = clamp_percent(density_percent, 50.0)

    if p >= 80:
        min_px, max_px = 18, 28
        std_ratio = 0.12
    elif p >= 60:
        min_px, max_px = 20, 32
        std_ratio = 0.13
    elif p <= 25:
        min_px, max_px = 24, 38
        std_ratio = 0.14
    else:
        min_px, max_px = 22, 34
        std_ratio = 0.13

    return {
        "render.text.font_size.min_px": min_px,
        "render.text.font_size.max_px": max_px,
        "render.text.font_size.distribution": "gaussian",
        "render.text.font_size.mean_ratio": 0.68,
        "render.text.font_size.std_ratio": std_ratio,
    }


def _natural_word_bank_line_style_dist() -> Dict[str, float]:
    return {
        "prose": 1.0,
        "mixed": 0.0,
        "code": 0.0,
        "mathish": 0.0,
        "bars": 0.0,
        "noisy": 0.0,
    }


def _font_size_overrides(state: WebGuiState) -> Dict[str, Any]:
    profile = str(_widget_value(state.font_size_profile_select, "Balanced"))
    size_range = font_size_profile_to_range(profile)

    if profile == "Custom":
        min_px = int(_as_float(_widget_value(state.font_min_px_input, 10), 10))
        max_px = int(_as_float(_widget_value(state.font_max_px_input, 18), 18))

        if min_px > max_px:
            min_px, max_px = max_px, min_px
    else:
        min_px = int(size_range["min_px"])
        max_px = int(size_range["max_px"])

    return {
        "render.text.font_size.min_px": min_px,
        "render.text.font_size.max_px": max_px,
        "render.text.font_size.distribution": "gaussian",
        "render.text.font_size.mean_ratio": 0.68,
        "render.text.font_size.std_ratio": 0.18,
    }


def _layout_overrides(state: WebGuiState) -> Dict[str, Any]:
    density_percent = _widget_value(state.density_percent_input, 50)
    layout_randomness_percent = _widget_value(
        state.layout_randomness_percent_input,
        25,
    )
    layout_randomness_percent = min(
        float(layout_randomness_percent),
        55.0,
    )    
    negative_space_profile = _widget_value(
        getattr(state, "negative_space_profile_select", None),
        "Controlled",
    )

    line_gap_policy = layout_randomness_percent_to_line_gap(
        layout_randomness_percent
    )

    occupancy_policy = negative_space_profile_to_occupancy(
        negative_space_profile
    )

    return {
        "dist.density_dist": negative_space_profile_to_density_dist(
            density_percent,
            negative_space_profile,
        ),
        "layout.targets": negative_space_profile_to_layout_targets(
            negative_space_profile,
        ),

        "layout.line_gap": line_gap_policy,
        "layout.line_gap_random_scale": spacing_percent_to_line_gap_scale(
            layout_randomness_percent
        ),

        "layout.occupancy.enable": True,
        "layout.occupancy.whitespace_strategy": occupancy_policy["whitespace_strategy"],
        "layout.occupancy.spread_percent": occupancy_policy["spread_percent"],
        "layout.occupancy.min_gap_px": occupancy_policy["min_gap_px"],
        "layout.occupancy.max_place_attempts": occupancy_policy["max_place_attempts"],
        "layout.occupancy.target_fill_ratio": occupancy_policy["target_fill_ratio"],

        "content.hard_negative_page_prob": 0.0,

        **negative_space_profile_to_qc_overrides(negative_space_profile),
    }


def collect_simple_overrides(state: WebGuiState) -> Dict[str, Any]:
    if state.dataset_goal_select is None:
        return {}

    goal = str(_widget_value(state.dataset_goal_select, "Quick OCR Dataset"))
    character = str(_widget_value(state.dataset_character_select, "Balanced"))

    text_length = (
        str(_widget_value(state.text_length_select, "Balanced blocks"))
        if state.text_length_select is not None
        else "Balanced blocks"
    )

    diversity_strength = (
        str(_widget_value(state.diversity_strength_select, "Balanced diversity"))
        if state.diversity_strength_select is not None
        else "Balanced diversity"
    )

    # Public first version keeps business templates disabled.
    document_template = "Generic random document"

    mix = current_content_mix(state)
    density_percent = _widget_value(state.density_percent_input, 50)

    overrides = merge_maps(
        DOCUMENT_TEMPLATE_PRESETS.get(document_template, {}),
        DATASET_GOAL_PRESETS.get(goal, {}),
        DATASET_CHARACTER_PRESETS.get(character, {}),
        TEXT_LENGTH_PRESETS.get(text_length, {}),
        DIVERSITY_STRENGTH_PRESETS.get(diversity_strength, {}),
        {
            "content.block_mix": mix,

            # Main web generator is text/table only.
            # LaTeX is handled by the dedicated LaTeX Renderer page.
            "render.latex.enable": False,
        },

        # Density-conditioned font size:
        # dense -> smaller font, sparse -> larger font.
        _density_conditioned_font_size_overrides(
            state,
            density_percent,
        ),

        _layout_overrides(state),
    )

    # Density-conditioned noise:
    # dense/small-text pages should not receive too much heavy noise.
    #
    # However, the visual-character preset should not be erased completely.
    # Example: "Stress Test" intentionally requests heavy noise. Density may
    # cap it for readability, but it should still remain visibly stronger.
    density_noise_dist = _density_conditioned_noise_dist(density_percent)
    character_noise_dist = DATASET_CHARACTER_PRESETS.get(character, {}).get(
        "dist.noise_level_dist"
    )

    if isinstance(character_noise_dist, dict):
        character_heavy = float(character_noise_dist.get("heavy", 0.0) or 0.0)
        density_heavy = float(density_noise_dist.get("heavy", 0.0) or 0.0)

        if character_heavy >= 0.40 and character_heavy > density_heavy:
            effective_heavy = min(character_heavy, 0.35)
            remaining = max(0.0, 1.0 - effective_heavy)

            clean = float(density_noise_dist.get("clean", 0.0) or 0.0)
            medium = float(density_noise_dist.get("medium", 0.0) or 0.0)
            base = clean + medium

            if base > 0.0:
                density_noise_dist = {
                    "clean": remaining * clean / base,
                    "medium": remaining * medium / base,
                    "heavy": effective_heavy,
                }
            else:
                density_noise_dist = {
                    "clean": remaining,
                    "medium": 0.0,
                    "heavy": effective_heavy,
                }

    overrides["dist.noise_level_dist"] = density_noise_dist

    # ---------------------------------------------------------
    # User-controlled text length.
    # These values intentionally win over TEXT_LENGTH_PRESETS.
    # ---------------------------------------------------------
    text_min = _as_int_clamped(
        _widget_value(getattr(state, "text_min_words_input", None), 25),
        25,
        1,
        5000,
    )
    text_max = _as_int_clamped(
        _widget_value(getattr(state, "text_max_words_input", None), 90),
        90,
        1,
        10000,
    )
    text_min, text_max = _ordered_pair(text_min, text_max)

    sent_min = _as_int_clamped(
        _widget_value(getattr(state, "sentence_min_input", None), 2),
        2,
        1,
        200,
    )
    sent_max = _as_int_clamped(
        _widget_value(getattr(state, "sentence_max_input", None), 6),
        6,
        1,
        500,
    )
    sent_min, sent_max = _ordered_pair(sent_min, sent_max)

    overrides["content.words"] = {
        "min_words": text_min,
        "max_words": text_max,
        "separator": " ",
    }

    overrides["content.sentences"] = {
        "min_sentences": sent_min,
        "max_sentences": sent_max,
        "separator": " ",
    }

    # ---------------------------------------------------------
    # Text generation mode.
    # The GUI exposes user-friendly labels, but the backend still
    # receives stable config keys: content.source_mode/text_mode.
    # ---------------------------------------------------------
    mode = (
        str(_widget_value(state.content_source_mode_select, "word_bank"))
        if state.content_source_mode_select is not None
        else "word_bank"
    )

    if mode == "word_bank":
        overrides["content.source_mode"] = "content_bank"
        overrides["content.text_mode"] = "words"

    elif mode == "sentence_bank":
        overrides["content.source_mode"] = "content_bank"
        overrides["content.text_mode"] = "sentences"

    elif mode == "mixed_bank":
        overrides["content.source_mode"] = "content_bank"
        overrides["content.text_mode"] = "mixed"
        overrides["content.mixed_probs"] = {
            "chars": 0.0,
            "words": 0.75,
            "sentences": 0.25,
        }

    elif mode == "random_chars":
        overrides["content.source_mode"] = "random_chars"
        overrides["content.text_mode"] = "chars"

    else:
        # Backward-compatible fallback for older UI values such as
        # "content_bank".
        overrides["content.source_mode"] = "content_bank"
        overrides["content.text_mode"] = "words"

    # ---------------------------------------------------------
    # Natural multilingual word-bank policy.
    #
    # This keeps content_bank/words mode, but asks TextProvider
    # to mix different alphabet profiles inside the same group.
    #
    # scripts_dist is derived from alphabet_mix, so content language
    # and render script choices stay aligned.
    # ---------------------------------------------------------
    if (
        overrides.get("content.source_mode") == "content_bank"
        and overrides.get("content.text_mode") in {"words", "mixed"}
    ):
        alphabet_mix = _natural_multilingual_alphabet_mix()

        overrides["content.word_bank_policy"] = {
            "enable": True,
            "primary": "alphabet",
            "mix_strategy": "dominant_sentence",
            "group_multilingual": False,
            "min_alphabets_per_group": 1,
            "sentence_language_mode": "dominant",
            "sentence_language_switch_prob": 0.0,
            "table_cell_sentence_prob": 0.15,
            "table_cell_sentence_min_words": 2,
            "table_cell_sentence_max_words": 6,
            "alphabet_mix": alphabet_mix,
        }



        overrides["render.text.scripts_dist"] = _scripts_dist_from_alphabet_mix(
            alphabet_mix
        )

        # Word-bank natural mode should not produce code/math/bar stress lines.
        # Those can be separate presets later.
        overrides["render.text.line_style_dist"] = _natural_word_bank_line_style_dist()

        overrides["render.text.babel_mode_prob"] = 0.0
        overrides["render.text.code_switch_prob"] = 0.0

        # OCR-safe natural mode.
        # Unsafe generated lines should not make the page sparse;
        # after retries, renderer uses deterministic safe fallback text.
        overrides["render.text.safe_ocr_line_guard"] = True
        overrides["render.text.max_text_generation_attempts"] = 8
        overrides["render.text.unsafe_retry_policy"] = "safe_fallback"
        overrides["render.text.safe_fallback_after_retries"] = True
        overrides["render.text.reject_pil_default_font"] = True

        
        overrides["render.text.reject_overlapping_text"] = False


    # Main GUI should generate filled, useful OCR tables.
    overrides["layout.table_empty_cell_scale"] = 0.0
    overrides["layout.table_merge_cell_scale"] = 0.15


    # ---------------------------------------------------------
    # User-controlled table size.
    # The layout/table backend will consume this through config.
    # ---------------------------------------------------------
    table_min_rows = _as_int_clamped(
        _widget_value(getattr(state, "table_min_rows_input", None), 6),
        6,
        1,
        200,
    )
    table_max_rows = _as_int_clamped(
        _widget_value(getattr(state, "table_max_rows_input", None), 18),
        18,
        1,
        500,
    )
    table_min_cols = _as_int_clamped(
        _widget_value(getattr(state, "table_min_cols_input", None), 3),
        3,
        1,
        80,
    )
    table_max_cols = _as_int_clamped(
        _widget_value(getattr(state, "table_max_cols_input", None), 10),
        10,
        1,
        120,
    )

    table_min_rows, table_max_rows = _ordered_pair(table_min_rows, table_max_rows)
    table_min_cols, table_max_cols = _ordered_pair(table_min_cols, table_max_cols)

    overrides["render.non_text.table_shape"] = {
        "min_rows": table_min_rows,
        "max_rows": table_max_rows,
        "min_cols": table_min_cols,
        "max_cols": table_max_cols,
    }

    # Safety: main web generator never enables LaTeX.
    overrides["content.block_mix"] = mix
    overrides["render.latex.enable"] = False

    return overrides
