from __future__ import annotations

import json
from pathlib import Path

from docsynthfab.content.bootstrap import (
    ensure_content_bank,
    reset_content_to_samples,
    reset_generated_content_files,
)


class Cfg:
    def __init__(self, raw: dict):
        self.raw = raw


def _cfg() -> Cfg:
    return Cfg(
        {
            "content": {
                "source": {
                    "words_csv": "data/content/words.csv",
                    "sentences_csv": "data/content/sentences.csv",
                    "word_banks_dir": "data/content/word_banks",
                    "generated_json": "data/content/generated/content_bank.json",
                    "label_registry_csv": "data/content/generated/label_registry.csv",
                },
                "generate_json_if_missing": True,
                "regenerate_json_on_start": False,
            }
        }
    )


def test_ensure_content_bank_creates_sample_csvs_and_generated_json(
    tmp_path: Path,
    monkeypatch,
):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    monkeypatch.chdir(project_root)

    info = ensure_content_bank(_cfg())

    words_csv = Path(info["words_csv"])
    sentences_csv = Path(info["sentences_csv"])
    word_banks_dir = Path(info["word_banks_dir"])
    generated_json = Path(info["generated_json"])
    label_registry_csv = Path(info["label_registry_csv"])

    assert words_csv.exists()
    assert sentences_csv.exists()
    assert word_banks_dir.exists()
    assert word_banks_dir.is_dir()
    assert generated_json.exists()
    assert label_registry_csv.exists()

    obj = json.loads(generated_json.read_text(encoding="utf-8"))

    assert obj["version"] == "content-bank-v1"
    assert len(obj["words"]) > 0
    assert len(obj["sentences"]) > 0


def test_ensure_content_bank_uses_relative_paths_from_current_workdir(
    tmp_path: Path,
    monkeypatch,
):
    project_root = tmp_path / "proj"
    data_dir = project_root / "data" / "content"
    data_dir.mkdir(parents=True)

    (data_dir / "words.csv").write_text(
        "word,lang,script,alphabet_profile,weight,category,enabled\n"
        "alpha,en,latin,latin_basic,1.0,general,1\n"
        "beta,en,latin,latin_basic,1.0,general,1\n",
        encoding="utf-8",
    )
    (data_dir / "sentences.csv").write_text(
        "text,lang,script,alphabet_profile,weight,category,enabled\n"
        "hello world,en,latin,latin_basic,1.0,general,1\n"
        "another line,en,latin,latin_basic,1.0,general,1\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(project_root)

    info = ensure_content_bank(_cfg())

    assert Path(info["words_csv"]) == (
        project_root / "data" / "content" / "words.csv"
    ).resolve()
    assert Path(info["sentences_csv"]) == (
        project_root / "data" / "content" / "sentences.csv"
    ).resolve()
    assert Path(info["word_banks_dir"]) == (
        project_root / "data" / "content" / "word_banks"
    ).resolve()
    assert Path(info["generated_json"]).exists()


def test_ensure_content_bank_returns_resolved_absolute_paths(
    tmp_path: Path,
    monkeypatch,
):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    monkeypatch.chdir(project_root)

    info = ensure_content_bank(_cfg())

    assert Path(info["words_csv"]).is_absolute()
    assert Path(info["sentences_csv"]).is_absolute()
    assert Path(info["word_banks_dir"]).is_absolute()
    assert Path(info["generated_json"]).is_absolute()
    assert Path(info["label_registry_csv"]).is_absolute()


def test_ensure_content_bank_does_not_regenerate_existing_json_when_disabled(
    tmp_path: Path,
    monkeypatch,
):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    monkeypatch.chdir(project_root)

    cfg = _cfg()

    info = ensure_content_bank(cfg)
    generated_json = Path(info["generated_json"])

    generated_json.write_text(
        json.dumps({"version": "custom", "words": [], "sentences": []}),
        encoding="utf-8",
    )

    info2 = ensure_content_bank(cfg)
    loaded = json.loads(Path(info2["generated_json"]).read_text(encoding="utf-8"))

    assert loaded["version"] == "custom"


def test_ensure_content_bank_regenerates_when_regenerate_on_start_true(
    tmp_path: Path,
    monkeypatch,
):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    monkeypatch.chdir(project_root)

    cfg = _cfg()
    info = ensure_content_bank(cfg)

    generated_json = Path(info["generated_json"])
    generated_json.write_text(
        json.dumps({"version": "custom", "words": [], "sentences": []}),
        encoding="utf-8",
    )

    cfg.raw["content"]["regenerate_json_on_start"] = True

    info2 = ensure_content_bank(cfg)
    loaded = json.loads(Path(info2["generated_json"]).read_text(encoding="utf-8"))

    assert loaded["version"] == "content-bank-v1"
    assert len(loaded["words"]) > 0


def test_ensure_content_bank_does_not_generate_json_when_disabled_and_existing_missing(
    tmp_path: Path,
    monkeypatch,
):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    monkeypatch.chdir(project_root)

    cfg = _cfg()
    cfg.raw["content"]["generate_json_if_missing"] = False
    cfg.raw["content"]["regenerate_json_on_start"] = False

    info = ensure_content_bank(cfg)

    assert Path(info["words_csv"]).exists()
    assert Path(info["sentences_csv"]).exists()
    assert Path(info["label_registry_csv"]).exists()
    assert Path(info["word_banks_dir"]).exists()

    assert not Path(info["generated_json"]).exists()


def test_reset_generated_content_files_rebuilds_json_and_label_registry(
    tmp_path: Path,
    monkeypatch,
):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    monkeypatch.chdir(project_root)

    cfg = _cfg()
    info = ensure_content_bank(cfg)

    generated_json = Path(info["generated_json"])
    label_registry_csv = Path(info["label_registry_csv"])

    generated_json.write_text(
        json.dumps({"version": "custom", "words": [], "sentences": []}),
        encoding="utf-8",
    )
    label_registry_csv.write_text("custom", encoding="utf-8")

    out = reset_generated_content_files(cfg)

    generated_json = Path(out["generated_json"])
    label_registry_csv = Path(out["label_registry_csv"])

    loaded = json.loads(generated_json.read_text(encoding="utf-8"))

    assert loaded["version"] == "content-bank-v1"
    assert label_registry_csv.exists()
    assert "kind,value" in label_registry_csv.read_text(encoding="utf-8-sig")


def test_reset_generated_content_files_builds_json_even_when_generate_disabled(
    tmp_path: Path,
    monkeypatch,
):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    monkeypatch.chdir(project_root)

    cfg = _cfg()
    cfg.raw["content"]["generate_json_if_missing"] = False

    ensure_content_bank(cfg)

    out = reset_generated_content_files(cfg)

    assert Path(out["generated_json"]).exists()

    loaded = json.loads(Path(out["generated_json"]).read_text(encoding="utf-8"))

    assert loaded["version"] == "content-bank-v1"
    assert len(loaded["words"]) > 0
    assert len(loaded["sentences"]) > 0


def test_reset_content_to_samples_overwrites_csvs_and_rebuilds_json(
    tmp_path: Path,
    monkeypatch,
):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    monkeypatch.chdir(project_root)

    cfg = _cfg()
    info = ensure_content_bank(cfg)

    Path(info["words_csv"]).write_text("word\ncustom\n", encoding="utf-8")
    Path(info["sentences_csv"]).write_text("text\ncustom sentence\n", encoding="utf-8")

    out = reset_content_to_samples(cfg)

    words_text = Path(out["words_csv"]).read_text(encoding="utf-8")
    sentences_text = Path(out["sentences_csv"]).read_text(encoding="utf-8")
    loaded = json.loads(Path(out["generated_json"]).read_text(encoding="utf-8"))

    assert "invoice" in words_text
    assert "This is a sample sentence." in sentences_text
    assert loaded["version"] == "content-bank-v1"
    assert len(loaded["words"]) > 0
    assert len(loaded["sentences"]) > 0


def test_reset_content_to_samples_preserves_word_banks_dir(
    tmp_path: Path,
    monkeypatch,
):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    monkeypatch.chdir(project_root)

    cfg = _cfg()

    out = reset_content_to_samples(cfg)

    assert Path(out["word_banks_dir"]).exists()
    assert Path(out["word_banks_dir"]).is_dir()