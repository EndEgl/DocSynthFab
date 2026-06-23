from __future__ import annotations

import csv
import json
from pathlib import Path

from docsynthfab.content.bank_builder import (
    _as_enabled,
    _as_weight,
    _collect_label_registry,
    _dedupe_items,
    _load_sentences_csv,
    _load_word_banks_dir,
    _load_words_csv,
    build_content_bank_json,
)


def test_as_enabled_parses_false_like_values():
    assert _as_enabled(None) is True
    assert _as_enabled("1") is True
    assert _as_enabled("true") is True
    assert _as_enabled("yes") is True
    assert _as_enabled("on") is True

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


def test_load_words_csv_skips_disabled_and_empty_rows(tmp_path: Path):
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


def test_load_words_csv_adds_source_when_source_name_is_given(tmp_path: Path):
    path = tmp_path / "words.csv"
    path.write_text(
        "word,lang,script,alphabet_profile,weight,category,enabled\n"
        "alpha,en,latin,latin_basic,1.0,general,1\n",
        encoding="utf-8",
    )

    words = _load_words_csv(path, source_name="legacy_words.csv")

    assert len(words) == 1
    assert words[0]["source"] == "legacy_words.csv"


def test_load_words_csv_missing_file_returns_empty_list(tmp_path: Path):
    assert _load_words_csv(tmp_path / "missing.csv") == []


def test_load_sentences_csv_skips_disabled_and_empty_rows(tmp_path: Path):
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


def test_load_sentences_csv_missing_file_returns_empty_list(tmp_path: Path):
    assert _load_sentences_csv(tmp_path / "missing.csv") == []


def test_dedupe_items_removes_duplicate_text_lang_script_alphabet():
    items = [
        {
            "text": "alpha",
            "lang": "en",
            "script": "latin",
            "alphabet_profile": "latin_basic",
            "weight": 1.0,
        },
        {
            "text": "alpha",
            "lang": "EN",
            "script": "LATIN",
            "alphabet_profile": "LATIN_BASIC",
            "weight": 99.0,
        },
        {
            "text": "alpha",
            "lang": "tr",
            "script": "latin",
            "alphabet_profile": "latin_tr",
            "weight": 1.0,
        },
        {
            "text": "",
            "lang": "en",
            "script": "latin",
            "alphabet_profile": "latin_basic",
            "weight": 1.0,
        },
    ]

    out = _dedupe_items(items)

    assert len(out) == 2
    assert out[0]["lang"] == "en"
    assert out[1]["lang"] == "tr"


def test_load_word_banks_dir_reads_sorted_csv_files_and_adds_source(tmp_path: Path):
    bank_dir = tmp_path / "word_banks"
    bank_dir.mkdir()

    (bank_dir / "b.csv").write_text(
        "word,lang,script,alphabet_profile,weight,category,enabled\n"
        "beta,en,latin,latin_basic,1.0,general,1\n",
        encoding="utf-8",
    )
    (bank_dir / "a.csv").write_text(
        "word,lang,script,alphabet_profile,weight,category,enabled\n"
        "alpha,en,latin,latin_basic,1.0,general,1\n",
        encoding="utf-8",
    )

    words = _load_word_banks_dir(bank_dir)

    assert [w["text"] for w in words] == ["alpha", "beta"]
    assert words[0]["source"] == "word_banks/a.csv"
    assert words[1]["source"] == "word_banks/b.csv"


def test_load_word_banks_dir_missing_none_or_file_path_returns_empty_list(tmp_path: Path):
    assert _load_word_banks_dir(None) == []
    assert _load_word_banks_dir(tmp_path / "missing") == []

    file_path = tmp_path / "not_dir.csv"
    file_path.write_text("word\nalpha\n", encoding="utf-8")

    assert _load_word_banks_dir(file_path) == []


def test_collect_label_registry_deduplicates_and_sorts():
    words = [
        {
            "lang": "en",
            "script": "latin",
            "alphabet_profile": "latin_basic",
            "source": "words.csv",
        },
        {
            "lang": "tr",
            "script": "latin",
            "alphabet_profile": "latin_tr",
            "source": "word_banks/tr.csv",
        },
    ]
    sentences = [
        {
            "lang": "en",
            "script": "latin",
            "alphabet_profile": "latin_basic",
        },
    ]

    rows = _collect_label_registry(words, sentences)

    assert {"kind": "lang", "value": "en"} in rows
    assert {"kind": "lang", "value": "tr"} in rows
    assert {"kind": "script", "value": "latin"} in rows
    assert {"kind": "alphabet_profile", "value": "latin_basic"} in rows
    assert {"kind": "alphabet_profile", "value": "latin_tr"} in rows
    assert {"kind": "source", "value": "words.csv"} in rows
    assert {"kind": "source", "value": "word_banks/tr.csv"} in rows

    assert rows == sorted(rows, key=lambda x: (x["kind"], x["value"]))


def test_build_content_bank_json_writes_json_and_label_registry(tmp_path: Path):
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


def test_build_content_bank_json_merges_legacy_words_and_word_banks_with_dedupe(
    tmp_path: Path,
):
    words_csv = tmp_path / "words.csv"
    sentences_csv = tmp_path / "sentences.csv"
    word_banks_dir = tmp_path / "word_banks"
    out_json = tmp_path / "generated" / "content_bank.json"
    label_registry = tmp_path / "generated" / "label_registry.csv"

    word_banks_dir.mkdir()

    words_csv.write_text(
        "word,lang,script,alphabet_profile,weight,category,enabled\n"
        "alpha,en,latin,latin_basic,1.0,general,1\n"
        "legacy_only,en,latin,latin_basic,1.0,general,1\n",
        encoding="utf-8",
    )

    (word_banks_dir / "extra.csv").write_text(
        "word,lang,script,alphabet_profile,weight,category,enabled\n"
        "alpha,en,latin,latin_basic,5.0,general,1\n"
        "bank_only,tr,latin,latin_tr,1.0,general,1\n",
        encoding="utf-8",
    )

    sentences_csv.write_text(
        "text,lang,script,alphabet_profile,weight,category,enabled\n"
        "Hello world,en,latin,latin_basic,1.0,general,1\n",
        encoding="utf-8",
    )

    obj = build_content_bank_json(
        words_csv_path=words_csv,
        sentences_csv_path=sentences_csv,
        word_banks_dir=word_banks_dir,
        out_json_path=out_json,
        label_registry_csv_path=label_registry,
    )

    texts = [item["text"] for item in obj["words"]]

    assert texts == ["alpha", "legacy_only", "bank_only"]

    assert obj["meta"]["legacy_words_count"] == 2
    assert obj["meta"]["word_bank_words_count"] == 2
    assert obj["meta"]["words_count"] == 3
    assert obj["meta"]["sentences_count"] == 1
    assert obj["meta"]["word_banks_dir"] == str(word_banks_dir)

    label_text = label_registry.read_text(encoding="utf-8-sig")

    assert "source,word_banks/extra.csv" in label_text