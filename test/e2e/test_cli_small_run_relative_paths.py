from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.e2e
@pytest.mark.path_resolution
def test_cli_small_run_relative_paths(tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True)

    src_dir = Path("src").resolve()
    fixture_cfg = Path("test/fixtures/configs/minimal_valid.yaml").resolve()
    fixture_words = Path("test/fixtures/content/words.csv").resolve()
    fixture_sentences = Path("test/fixtures/content/sentences.csv").resolve()

    shutil.copytree(src_dir, project_root / "src")
    (project_root / "configs").mkdir(parents=True)
    (project_root / "data" / "content").mkdir(parents=True)

    shutil.copy2(fixture_cfg, project_root / "configs" / "minimal_valid.yaml")
    shutil.copy2(fixture_words, project_root / "data" / "content" / "words.csv")
    shutil.copy2(fixture_sentences, project_root / "data" / "content" / "sentences.csv")

    cmd = [
        sys.executable,
        "-m",
        "ai1_gen.cli",
        "--config",
        "configs/minimal_valid.yaml",
        "--out",
        "out",
        "--pages",
        "1",
        "--workers",
        "1",
        "--seed",
        "123",
    ]

    env = dict(**__import__("os").environ)
    env["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        cmd,
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    out_root = project_root / "out"
    assert out_root.exists()
    assert (out_root / "qc_summary.json").exists()
    assert (out_root / "gt_pages.jsonl").exists()
    assert (out_root / "splits" / "train.txt").exists()