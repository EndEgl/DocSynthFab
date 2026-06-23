from __future__ import annotations

import json
import random
from pathlib import Path

from docsynthfab.content.text_provider import TextProvider


def _bank() -> dict:
    return {
        "version": "content-bank-v1",
        "words": [
            {
                "text": "alpha",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 1.0,
                "category": "general",
            },
            {
                "text": "beta",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 1.0,
                "category": "general",
            },
            {
                "text": "veri",
                "lang": "tr",
                "script": "latin",
                "alphabet_profile": "latin_tr",
                "weight": 1.0,
                "category": "general",
            },
        ],
        "sentences": [
            {
                "text": "Hello world.",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 1.0,
                "category": "general",
            },
            {
                "text": "Bu bir cümledir.",
                "lang": "tr",
                "script": "latin",
                "alphabet_profile": "latin_tr",
                "weight": 1.0,
                "category": "general",
            },
        ],
    }


def test_from_json_loads_bank_file(tmp_path: Path):
    path = tmp_path / "bank.json"
    path.write_text(json.dumps(_bank(), ensure_ascii=False), encoding="utf-8")

    provider = TextProvider.from_json(
        path,
        {"text_mode": "words"},
        random.Random(123),
    )

    assert len(provider.words) == 3
    assert len(provider.sentences) == 2


def test_next_text_returns_empty_string_for_math_line():
    provider = TextProvider(_bank(), {"text_mode": "words"}, random.Random(123))

    assert provider.next_text(line_type="math") == ""


def test_chars_mode_generates_text_within_length_range():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "chars",
            "chars": {
                "charset": "abc",
                "min_len": 5,
                "max_len": 7,
            },
        },
        random.Random(123),
    )

    text = provider.next_text()

    assert 5 <= len(text) <= 7
    assert set(text).issubset({"a", "b", "c"})


def test_words_mode_sequential_uses_bank_order():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "text_order": "sequential",
            "words": {
                "min_words": 1,
                "max_words": 1,
                "join_with": " ",
            },
        },
        random.Random(123),
    )

    assert provider.next_text() == "alpha"
    assert provider.next_text() == "beta"
    assert provider.next_text() == "veri"
    assert provider.next_text() == "alpha"


def test_sentences_mode_sequential_uses_bank_order():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "sentences",
            "text_order": "sequential",
            "sentences": {
                "min_sentences": 1,
                "max_sentences": 1,
                "separator": " ",
            },
        },
        random.Random(123),
    )

    assert provider.next_text() == "Hello world."
    assert provider.next_text() == "Bu bir cümledir."
    assert provider.next_text() == "Hello world."


def test_filter_language_limits_items_when_match_exists():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "text_order": "sequential",
            "filter": {
                "language_label": "tr",
            },
            "words": {
                "min_words": 1,
                "max_words": 1,
            },
        },
        random.Random(123),
    )

    assert provider.next_text() == "veri"
    assert provider.next_text() == "veri"


def test_filter_script_limits_items_when_match_exists():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "text_order": "sequential",
            "filter": {
                "script_label": "latin",
            },
            "words": {
                "min_words": 1,
                "max_words": 1,
            },
        },
        random.Random(123),
    )

    assert provider.next_text() == "alpha"


def test_filter_alphabet_limits_items_when_match_exists():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "text_order": "sequential",
            "filter": {
                "alphabet_profile": "latin_tr",
            },
            "words": {
                "min_words": 1,
                "max_words": 1,
            },
        },
        random.Random(123),
    )

    assert provider.next_text() == "veri"


def test_filter_falls_back_to_original_items_when_no_match_exists():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "text_order": "sequential",
            "filter": {
                "language_label": "de",
            },
            "words": {
                "min_words": 1,
                "max_words": 1,
            },
        },
        random.Random(123),
    )

    assert provider.next_text() == "alpha"


def test_random_chars_source_mode_ignores_bank_and_forces_chars():
    provider = TextProvider(
        _bank(),
        {
            "source_mode": "random_chars",
            "chars": {
                "charset": "xyz",
                "min_len": 4,
                "max_len": 4,
            },
        },
        random.Random(123),
    )

    text = provider.next_text()

    assert len(text) == 4
    assert set(text).issubset({"x", "y", "z"})


def test_words_mode_falls_back_to_chars_when_word_bank_empty():
    provider = TextProvider(
        {"words": [], "sentences": []},
        {
            "text_mode": "words",
            "chars": {
                "charset": "ab",
                "min_len": 3,
                "max_len": 3,
            },
        },
        random.Random(123),
    )

    text = provider.next_text()

    assert len(text) == 3
    assert set(text).issubset({"a", "b"})


def test_sentences_mode_falls_back_to_words_or_chars_when_sentence_bank_empty():
    provider = TextProvider(
        {
            "words": [
                {
                    "text": "alpha",
                    "lang": "en",
                    "script": "latin",
                    "alphabet_profile": "latin_basic",
                    "weight": 1.0,
                }
            ],
            "sentences": [],
        },
        {
            "text_mode": "sentences",
            "text_order": "sequential",
            "sentences": {
                "min_sentences": 1,
                "max_sentences": 1,
            },
            "words": {
                "min_words": 1,
                "max_words": 1,
            },
        },
        random.Random(123),
    )

    assert provider.next_text() == "alpha"


def test_mixed_mode_can_pick_configured_words_only():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "mixed",
            "mixed_probs": {
                "chars": 0.0,
                "words": 1.0,
                "sentences": 0.0,
            },
            "words": {
                "min_words": 1,
                "max_words": 1,
            },
        },
        random.Random(123),
    )

    assert provider.next_text() in {"alpha", "beta", "veri"}


def test_mixed_mode_can_pick_configured_sentences_only():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "mixed",
            "mixed_probs": {
                "chars": 0.0,
                "words": 0.0,
                "sentences": 1.0,
            },
            "sentences": {
                "min_sentences": 1,
                "max_sentences": 1,
            },
        },
        random.Random(123),
    )

    assert provider.next_text() in {"Hello world.", "Bu bir cümledir."}


def test_norm_weight_map_ignores_invalid_and_normalizes_positive_values():
    provider = TextProvider(_bank(), {"text_mode": "words"}, random.Random(123))

    out = provider._norm_weight_map(
        {
            " en ": 2,
            "tr": 2,
            "bad": "x",
            "zero": 0,
            "negative": -1,
            "": 10,
        }
    )

    assert out == {
        "en": 0.5,
        "tr": 0.5,
    }


def test_word_bank_policy_filters_by_alphabet_profile():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "text_order": "sequential",
            "word_bank_policy": {
                "enable": True,
                "primary": "alphabet",
                "alphabet_mix": {
                    "latin_tr": 1.0,
                },
            },
            "words": {
                "min_words": 1,
                "max_words": 1,
            },
        },
        random.Random(123),
    )

    assert provider.next_text() == "veri"
    assert provider.next_text() == "veri"


def test_word_bank_policy_filters_by_language():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "text_order": "sequential",
            "word_bank_policy": {
                "enable": True,
                "primary": "language",
                "language_mix": {
                    "tr": 1.0,
                },
            },
            "words": {
                "min_words": 1,
                "max_words": 1,
            },
        },
        random.Random(123),
    )

    assert provider.next_text() == "veri"


def test_word_bank_policy_filters_by_script():
    bank = {
        "words": [
            {
                "text": "alpha",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 1.0,
            },
            {
                "text": "gamma",
                "lang": "el",
                "script": "greek",
                "alphabet_profile": "greek",
                "weight": 1.0,
            },
        ],
        "sentences": [],
    }

    provider = TextProvider(
        bank,
        {
            "text_mode": "words",
            "text_order": "sequential",
            "word_bank_policy": {
                "enable": True,
                "primary": "script",
                "script_mix": {
                    "greek": 1.0,
                },
            },
            "words": {
                "min_words": 1,
                "max_words": 1,
            },
        },
        random.Random(123),
    )

    assert provider.next_text() == "gamma"


def test_table_cell_text_returns_short_word_group():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "word_bank_policy": {
                "enable": True,
                "alphabet_mix": {
                    "latin_basic": 1.0,
                },
                "table_cell_sentence_prob": 0.0,
            },
            "words": {
                "min_words": 1,
                "max_words": 3,
                "join_with": " ",
            },
        },
        random.Random(123),
    )

    text = provider.next_text(line_type="table_cell")

    assert text.strip()
    assert 1 <= len(text.split()) <= 3


def test_table_cell_sentence_prob_can_generate_short_sentence_like_group():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "word_bank_policy": {
                "enable": True,
                "alphabet_mix": {
                    "latin_basic": 1.0,
                },
                "table_cell_sentence_prob": 1.0,
                "table_cell_sentence_min_words": 2,
                "table_cell_sentence_max_words": 4,
            },
            "words": {
                "join_with": " ",
            },
        },
        random.Random(123),
    )

    text = provider.next_text(line_type="table_cell")

    assert text.strip()
    assert 2 <= len(text.split()) <= 4


def test_paragraph_line_type_expands_words_to_longer_body_text():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "word_bank_policy": {
                "enable": True,
                "alphabet_mix": {
                    "latin_basic": 1.0,
                },
            },
            "words": {
                "min_words": 1,
                "max_words": 3,
                "join_with": " ",
            },
        },
        random.Random(123),
    )

    text = provider.next_text(line_type="paragraph")

    assert len(text.split()) >= 8


def test_body_line_type_expands_words_to_longer_body_text():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "word_bank_policy": {
                "enable": True,
                "alphabet_mix": {
                    "latin_basic": 1.0,
                },
            },
            "words": {
                "min_words": 1,
                "max_words": 3,
                "join_with": " ",
            },
        },
        random.Random(123),
    )

    text = provider.next_text(line_type="body")

    assert len(text.split()) >= 8


def test_group_multilingual_forces_multiple_alphabets_when_available():
    bank = {
        "words": [
            {
                "text": "alpha",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 1.0,
            },
            {
                "text": "veri",
                "lang": "tr",
                "script": "latin",
                "alphabet_profile": "latin_tr",
                "weight": 1.0,
            },
            {
                "text": "gamma",
                "lang": "el",
                "script": "greek",
                "alphabet_profile": "greek",
                "weight": 1.0,
            },
        ],
        "sentences": [],
    }

    provider = TextProvider(
        bank,
        {
            "text_mode": "words",
            "word_bank_policy": {
                "enable": True,
                "group_multilingual": True,
                "sentence_language_mode": "mixed",
                "min_alphabets_per_group": 2,
                "alphabet_mix": {
                    "latin_basic": 1.0,
                    "latin_tr": 1.0,
                    "greek": 1.0,
                },
            },
            "words": {
                "min_words": 3,
                "max_words": 3,
                "join_with": " ",
            },
        },
        random.Random(123),
    )

    text = provider.next_text()
    words = set(text.split())

    assert len(words & {"alpha", "veri", "gamma"}) >= 2


def test_group_multilingual_falls_back_when_only_one_active_alphabet_exists():
    provider = TextProvider(
        _bank(),
        {
            "text_mode": "words",
            "text_order": "sequential",
            "word_bank_policy": {
                "enable": True,
                "group_multilingual": True,
                "sentence_language_mode": "mixed",
                "min_alphabets_per_group": 2,
                "alphabet_mix": {
                    "latin_tr": 1.0,
                },
            },
            "words": {
                "min_words": 1,
                "max_words": 1,
                "join_with": " ",
            },
        },
        random.Random(123),
    )

    assert provider.next_text() == "veri"


def test_zero_weights_fall_back_to_uniform_choice():
    bank = {
        "words": [
            {
                "text": "alpha",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 0.0,
            },
            {
                "text": "beta",
                "lang": "en",
                "script": "latin",
                "alphabet_profile": "latin_basic",
                "weight": 0.0,
            },
        ],
        "sentences": [],
    }

    provider = TextProvider(
        bank,
        {
            "text_mode": "words",
            "words": {
                "min_words": 1,
                "max_words": 1,
            },
        },
        random.Random(123),
    )

    assert provider.next_text() in {"alpha", "beta"}


def test_empty_word_and_sentence_bank_in_sentence_mode_falls_back_to_chars():
    provider = TextProvider(
        {
            "words": [],
            "sentences": [],
        },
        {
            "text_mode": "sentences",
            "chars": {
                "charset": "xy",
                "min_len": 4,
                "max_len": 4,
            },
        },
        random.Random(123),
    )

    text = provider.next_text()

    parts = text.split()

    assert parts
    assert all(len(part) == 4 for part in parts)
    assert set("".join(parts)).issubset({"x", "y"})