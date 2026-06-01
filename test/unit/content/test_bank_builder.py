from __future__ import annotations

import csv
import json

from ai1_gen.content.bank_builder import (
    _as_enabled,
    _as_weight,
    _collect_label_registry,
    _load_sentences_csv,
    _load_words_csv,
    build_content_bank_json,
)


def test_as_enabled_parses_false_like_values():
    assert _as_enabled(None) is True
    assert _as_enabled("1") is True
    assert _as_enabled("true") is True
    assert _as_enabled("0") is False
    assert _as_enabled("false") is False
    assert _as_enabled("no") is False
    assert _as_enabled("off") is False
    assert _as_enabled("") is False


def test_as_weight_defaults_and_clamps():
    assert _as_weight(None) == 1.0
    assert _as_weight("") == 1.0
    assert _as_weight("2.5") == 2.5
    assert _as_weight("-3") == 0.0
    assert _as_weight("bad") == 1.0


def test_load_words_csv_skips_disabled_and_empty_rows(tmp_path):
    path = tmp_path / "words.csv"
    path.write_text(
        "word,lang,script,alphabet_profile,weight,category,enabled\n"
        "alpha,en,latin,latin_basic,2.0,general,1\n"
        ",en,latin,latin_basic,1.0,general,1\n"
        "disabled,en,latin,latin_basic,1.0,general,0\n",
        encoding="utf-8",
    )

    words = _load_words_csv(path)

    assert len(words) == 1
    assert words[0]["text"] == "alpha"
    assert words[0]["lang"] == "en"
    assert words[0]["script"] == "latin"
    assert words[0]["alphabet_profile"] == "latin_basic"
    assert words[0]["weight"] == 2.0
    assert words[0]["category"] == "general"


def test_load_words_csv_missing_file_returns_empty_list(tmp_path):
    assert _load_words_csv(tmp_path / "missing.csv") == []


def test_load_sentences_csv_skips_disabled_and_empty_rows(tmp_path):
    path = tmp_path / "sentences.csv"
    path.write_text(
        "text,lang,script,alphabet_profile,weight,category,enabled\n"
        "Hello world,en,latin,latin_basic,1.5,general,1\n"
        ",en,latin,latin_basic,1.0,general,1\n"
        "Disabled sentence,en,latin,latin_basic,1.0,general,0\n",
        encoding="utf-8",
    )

    sentences = _load_sentences_csv(path)

    assert len(sentences) == 1
    assert sentences[0]["text"] == "Hello world"
    assert sentences[0]["lang"] == "en"
    assert sentences[0]["script"] == "latin"
    assert sentences[0]["alphabet_profile"] == "latin_basic"
    assert sentences[0]["weight"] == 1.5


def test_load_sentences_csv_missing_file_returns_empty_list(tmp_path):
    assert _load_sentences_csv(tmp_path / "missing.csv") == []


def test_collect_label_registry_deduplicates_and_sorts():
    words = [
        {"lang": "en", "script": "latin", "alphabet_profile": "latin_basic"},
        {"lang": "tr", "script": "latin", "alphabet_profile": "latin_tr"},
    ]
    sentences = [
        {"lang": "en", "script": "latin", "alphabet_profile": "latin_basic"},
    ]

    rows = _collect_label_registry(words, sentences)

    assert {"kind": "lang", "value": "en"} in rows
    assert {"kind": "lang", "value": "tr"} in rows
    assert {"kind": "script", "value": "latin"} in rows
    assert {"kind": "alphabet_profile", "value": "latin_basic"} in rows
    assert {"kind": "alphabet_profile", "value": "latin_tr"} in rows

    assert len(rows) == 5


def test_build_content_bank_json_writes_json_and_label_registry(tmp_path):
    words_csv = tmp_path / "words.csv"
    sentences_csv = tmp_path / "sentences.csv"
    out_json = tmp_path / "generated" / "content_bank.json"
    label_registry = tmp_path / "generated" / "label_registry.csv"

    words_csv.write_text(
        "word,lang,script,alphabet_profile,weight,category,enabled\n"
        "invoice,en,latin,latin_basic,1.0,business,1\n"
        "rapor,tr,latin,latin_tr,1.0,general,1\n",
        encoding="utf-8",
    )
    sentences_csv.write_text(
        "text,lang,script,alphabet_profile,weight,category,enabled\n"
        "Hello world,en,latin,latin_basic,1.0,general,1\n"
        "Bu bir cümledir,tr,latin,latin_tr,1.0,general,1\n",
        encoding="utf-8",
    )

    obj = build_content_bank_json(
        words_csv_path=words_csv,
        sentences_csv_path=sentences_csv,
        out_json_path=out_json,
        label_registry_csv_path=label_registry,
    )

    assert obj["version"] == "content-bank-v1"
    assert len(obj["words"]) == 2
    assert len(obj["sentences"]) == 2

    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert loaded == obj

    assert label_registry.exists()

    with label_registry.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    assert {"kind": "lang", "value": "en"} in rows
    assert {"kind": "lang", "value": "tr"} in rows