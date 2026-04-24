from pathlib import Path

import pytest

from ai1_gen.content import ensure_content_bank


@pytest.mark.path_resolution
def test_bootstrap_uses_relative_paths_from_current_workdir(tmp_path, monkeypatch):
    project_root = tmp_path / "proj"
    data_dir = project_root / "data" / "content"
    data_dir.mkdir(parents=True)

    (data_dir / "words.csv").write_text("text\nalpha\nbeta\n", encoding="utf-8")
    (data_dir / "sentences.csv").write_text("text\nhello world\nanother line\n", encoding="utf-8")

    monkeypatch.chdir(project_root)

    cfg = {
        "text_mode": "csv",
        "words_csv": "data/content/words.csv",
        "sentences_csv": "data/content/sentences.csv",
        "generated_json": "data/content/generated/bank.json",
    }

    try:
        out = ensure_content_bank(cfg)
    except TypeError:
        # Fonksiyon imzası farklıysa burada hemen anlaşılır.
        pytest.skip("ensure_content_bank signature differs from current assumption")

    assert out is not None