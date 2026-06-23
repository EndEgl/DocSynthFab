from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import pytest

from docsynthfab.content.bank_builder import build_content_bank_json
from docsynthfab.content.text_provider import TextProvider


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.integration
def test_turkish_utf8_csv_reaches_text_provider_without_corruption(tmp_path: Path, unicode_samples):
    words = tmp_path / "words.csv"
    sentences = tmp_path / "sentences.csv"
    out_json = tmp_path / "content_bank.json"
    registry = tmp_path / "label_registry.csv"

    _write_csv(
        words,
        ["word", "lang", "script", "alphabet_profile", "weight", "category", "enabled"],
        [{"word": "ölçü", "lang": "tr", "script": "tr", "alphabet_profile": "latin_tr", "weight": "1", "category": "test", "enabled": "1"}],
    )
    _write_csv(
        sentences,
        ["text", "lang", "script", "alphabet_profile", "weight", "category", "enabled"],
        [{"text": unicode_samples["turkish"], "lang": "tr", "script": "tr", "alphabet_profile": "latin_tr", "weight": "1", "category": "test", "enabled": "1"}],
    )

    bank = build_content_bank_json(
        words_csv_path=words,
        sentences_csv_path=sentences,
        out_json_path=out_json,
        label_registry_csv_path=registry,
    )

    provider = TextProvider(bank, {"text_mode": "sentences", "text_order": "sequential"}, random.Random(123))

    assert provider.next_text() == unicode_samples["turkish"]


@pytest.mark.integration
def test_cyrillic_csv_preserves_text_and_metadata(tmp_path: Path, unicode_samples):
    words = tmp_path / "words.csv"
    sentences = tmp_path / "sentences.csv"
    out_json = tmp_path / "content_bank.json"
    registry = tmp_path / "label_registry.csv"

    _write_csv(
        words,
        ["word", "lang", "script", "alphabet_profile", "weight", "category", "enabled"],
        [{"word": "пример", "lang": "ru", "script": "ru", "alphabet_profile": "cyrillic", "weight": "1", "category": "test", "enabled": "1"}],
    )
    _write_csv(
        sentences,
        ["text", "lang", "script", "alphabet_profile", "weight", "category", "enabled"],
        [{"text": unicode_samples["cyrillic"], "lang": "ru", "script": "ru", "alphabet_profile": "cyrillic", "weight": "1", "category": "test", "enabled": "1"}],
    )

    bank = build_content_bank_json(
        words_csv_path=words,
        sentences_csv_path=sentences,
        out_json_path=out_json,
        label_registry_csv_path=registry,
    )

    assert bank["sentences"][0]["text"] == unicode_samples["cyrillic"]
    assert bank["sentences"][0]["lang"] == "ru"
    assert bank["sentences"][0]["script"] == "ru"


@pytest.mark.integration
def test_mixed_content_provider_is_deterministic_with_seed(tmp_path: Path):
    bank = {
        "version": "content-bank-v1",
        "words": [{"text": "alpha", "lang": "en", "script": "latin", "alphabet_profile": "latin_basic", "weight": 1.0}],
        "sentences": [{"text": "Hello world.", "lang": "en", "script": "latin", "alphabet_profile": "latin_basic", "weight": 1.0}],
    }

    cfg = {
        "text_mode": "mixed",
        "mixed_probs": {"chars": 0.0, "words": 1.0, "sentences": 0.0},
        "words": {"min_words": 1, "max_words": 1},
    }

    a = TextProvider(bank, cfg, random.Random(123)).next_text()
    b = TextProvider(bank, cfg, random.Random(123)).next_text()

    assert a == b == "alpha"


@pytest.mark.integration
def test_empty_content_bank_falls_back_to_chars():
    provider = TextProvider(
        {"version": "content-bank-v1", "words": [], "sentences": []},
        {"text_mode": "words", "chars": {"charset": "ab", "min_len": 4, "max_len": 4}},
        random.Random(123),
    )

    text = provider.next_text()

    assert len(text) == 4
    assert set(text).issubset({"a", "b"})



