from __future__ import annotations

import json
import random

from ai1_gen.content.text_provider import TextProvider


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


def test_from_json_loads_bank_file(tmp_path):
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