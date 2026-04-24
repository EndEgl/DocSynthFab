from __future__ import annotations

import json
from pathlib import Path

from ai1_gen.content.bootstrap import ensure_content_bank


class CfgStub:
    def __init__(self, raw: dict) -> None:
        self.raw = raw


def test_content_bootstrap_builds_files_using_relative_project_root(tmp_path, monkeypatch):
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True)

    monkeypatch.chdir(project_root)

    cfg = CfgStub(
        raw={
            "content": {
                "source": {
                    "words_csv": "data/content/words.csv",
                    "sentences_csv": "data/content/sentences.csv",
                    "generated_json": "data/content/content_bank.json",
                },
                "generate_json_if_missing": True,
                "regenerate_json_on_start": False,
            }
        }
    )

    out = ensure_content_bank(cfg)

    words_csv = project_root / "data" / "content" / "words.csv"
    sentences_csv = project_root / "data" / "content" / "sentences.csv"
    generated_json = project_root / "data" / "content" / "content_bank.json"

    assert Path(out["words_csv"]) == words_csv
    assert Path(out["sentences_csv"]) == sentences_csv
    assert Path(out["generated_json"]) == generated_json

    assert words_csv.exists()
    assert sentences_csv.exists()
    assert generated_json.exists()

    obj = json.loads(generated_json.read_text(encoding="utf-8"))
    assert obj["version"] == "content-bank-v1"
    assert isinstance(obj["words"], list)
    assert isinstance(obj["sentences"], list)
    assert len(obj["words"]) > 0
    assert len(obj["sentences"]) > 0