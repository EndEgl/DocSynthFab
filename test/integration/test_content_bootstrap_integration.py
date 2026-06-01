from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai1_gen.content.bootstrap import (
    ensure_content_bank,
    reset_content_to_samples,
    reset_generated_content_files,
)


class CfgStub:
    def __init__(self, raw: dict):
        self.raw = raw


def _content_cfg() -> CfgStub:
    return CfgStub(
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


@pytest.mark.integration
def test_content_bootstrap_creates_csv_json_and_registry(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    out = ensure_content_bank(_content_cfg())

    assert Path(out["words_csv"]).exists()
    assert Path(out["sentences_csv"]).exists()
    assert Path(out["generated_json"]).exists()
    assert Path(out["label_registry_csv"]).exists()

    obj = json.loads(Path(out["generated_json"]).read_text(encoding="utf-8"))
    assert obj["version"] == "content-bank-v1"
    assert obj["words"]
    assert obj["sentences"]


@pytest.mark.integration
def test_content_bootstrap_preserves_existing_json_when_regenerate_disabled(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cfg = _content_cfg()
    out = ensure_content_bank(cfg)

    generated = Path(out["generated_json"])
    generated.write_text(
        json.dumps({"version": "custom", "words": [], "sentences": []}),
        encoding="utf-8",
    )

    out2 = ensure_content_bank(cfg)
    loaded = json.loads(Path(out2["generated_json"]).read_text(encoding="utf-8"))

    assert loaded["version"] == "custom"


@pytest.mark.integration
def test_content_bootstrap_regenerates_when_enabled(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cfg = _content_cfg()
    out = ensure_content_bank(cfg)

    generated = Path(out["generated_json"])
    generated.write_text(
        json.dumps({"version": "custom", "words": [], "sentences": []}),
        encoding="utf-8",
    )

    cfg.raw["content"]["regenerate_json_on_start"] = True

    out2 = ensure_content_bank(cfg)
    loaded = json.loads(Path(out2["generated_json"]).read_text(encoding="utf-8"))

    assert loaded["version"] == "content-bank-v1"
    assert loaded["words"]


@pytest.mark.integration
def test_reset_content_to_samples_rebuilds_csv_json_and_registry(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cfg = _content_cfg()
    ensure_content_bank(cfg)

    out = reset_content_to_samples(cfg)

    assert Path(out["words_csv"]).exists()
    assert Path(out["sentences_csv"]).exists()
    assert Path(out["generated_json"]).exists()
    assert Path(out["label_registry_csv"]).exists()

    generated = json.loads(Path(out["generated_json"]).read_text(encoding="utf-8"))
    assert generated["version"] == "content-bank-v1"

    out2 = reset_generated_content_files(cfg)
    assert Path(out2["generated_json"]).exists()