import pytest

from ai1_gen.content import ensure_content_bank


def test_bootstrap_handles_missing_relative_csv_files_without_crashing(tmp_path, monkeypatch):
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True)
    monkeypatch.chdir(project_root)

    cfg = {
        "text_mode": "csv",
        "words_csv": "data/content/missing_words.csv",
        "sentences_csv": "data/content/missing_sentences.csv",
        "generated_json": "data/content/generated/bank.json",
    }

    out = ensure_content_bank(cfg)
    assert out is not None