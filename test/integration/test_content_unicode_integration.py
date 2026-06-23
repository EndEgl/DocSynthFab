from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import pytest

from docsynthfab.content.bank_builder import build_content_bank_json
from docsynthfab.content.bootstrap import ensure_content_bank
from docsynthfab.content.text_provider import TextProvider


class CfgStub:
    def __init__(self, raw: dict):
        self.raw = raw


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.integration
def test_content_bootstrap_creates_generated_bank(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cfg = CfgStub(
        {
            "content": {
                "source": {
                    "words_csv": "data/content/words.csv",
                    "sentences_csv": "data/content/sentences.csv",
                    "generated_json": "data/content/generated/content_bank.json",
                    "label_registry_csv": "data/content/generated/label_registry.csv",
                },
                "generate_json_if_missing": True,
                "regenerate_json_on_start": False,
            }
        }
    )

    out = ensure_content_bank(cfg)

    assert Path(out["words_csv"]).exists()
    assert Path(out["sentences_csv"]).exists()
    assert Path(out["generated_json"]).exists()
    assert Path(out["label_registry_csv"]).exists()

    bank = json.loads(Path(out["generated_json"]).read_text(encoding="utf-8"))

    assert bank["version"] == "content-bank-v1"
    assert bank["words"]
    assert bank["sentences"]


@pytest.mark.integration
def test_turkish_utf8_csv_reaches_text_provider_without_corruption(
    tmp_path: Path,
    unicode_samples,
):
    words = tmp_path / "words.csv"
    sentences = tmp_path / "sentences.csv"
    out_json = tmp_path / "content_bank.json"
    registry = tmp_path / "label_registry.csv"

    _write_csv(
        words,
        ["word", "lang", "script", "alphabet_profile", "weight", "category", "enabled"],
        [
            {
                "word": "ölçü",
                "lang": "tr",
                "script": "tr",
                "alphabet_profile": "latin_tr",
                "weight": "1",
                "category": "test",
                "enabled": "1",
            }
        ],
    )

    _write_csv(
        sentences,
        ["text", "lang", "script", "alphabet_profile", "weight", "category", "enabled"],
        [
            {
                "text": unicode_samples["turkish"],
                "lang": "tr",
                "script": "tr",
                "alphabet_profile": "latin_tr",
                "weight": "1",
                "category": "test",
                "enabled": "1",
            }
        ],
    )

    bank = build_content_bank_json(
        words_csv_path=words,
        sentences_csv_path=sentences,
        out_json_path=out_json,
        label_registry_csv_path=registry,
    )

    provider = TextProvider(
        bank,
        {"text_mode": "sentences", "text_order": "sequential"},
        random.Random(123),
    )

    assert provider.next_text() == unicode_samples["turkish"]