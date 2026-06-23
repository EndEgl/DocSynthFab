from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from docsynthfab.config import AppConfig, load_config
from docsynthfab.orchestrator import RunOrchestrator, RunRequest


@pytest.mark.integration
def test_default_config_loads_as_app_config(default_config_path: Path):
    cfg = load_config(str(default_config_path))

    assert isinstance(cfg, AppConfig)
    assert cfg.pages > 0
    assert cfg.workers > 0
    assert isinstance(cfg.raw, dict)


@pytest.mark.integration
def test_preview_config_and_production_config_are_identical(
    default_config_path: Path,
    tmp_path: Path,
):
    orch = RunOrchestrator()

    overrides = {
        "content.block_mix": {"text": 85, "table": 10, "latex": 5},
        "content.source_mode": "random_chars",
        "content.text_mode": "chars",
        "layout.occupancy.enable": True,
        "layout.occupancy.whitespace_strategy": "spread",
        "layout.occupancy.max_place_attempts": 120,
    }

    raw_yaml = """
content:
  block_mix:
    text: 11
    table: 22
    latex: 67
layout:
  occupancy:
    whitespace_strategy: compact
"""

    preview_yaml = orch.build_effective_config_yaml_text(
        config_path=str(default_config_path),
        overrides=overrides,
        raw_yaml_override_text=raw_yaml,
        out_root=str(tmp_path / "out"),
        pages=9,
        workers=1,
        seed=777,
        smoke_test=False,
        export_targets=["native"],
    )

    preview_cfg = yaml.safe_load(preview_yaml)

    req = RunRequest(
        config_path=str(default_config_path),
        out_root=str(tmp_path / "out"),
        pages=9,
        workers=1,
        seed=777,
        smoke_test=False,
        export_targets=["native"],
        overrides=overrides,
        raw_yaml_override_text=raw_yaml,
    )

    production_cfg = orch.build_effective_config_dict(req)

    assert production_cfg == preview_cfg

    assert production_cfg["io"]["out_root"] == str(tmp_path / "out")
    assert production_cfg["run"]["pages"] == 9
    assert production_cfg["run"]["workers"] == 1
    assert production_cfg["run"]["seed"] == 777
    assert production_cfg["run"]["export_targets"] == ["native"]

    assert production_cfg["content"]["block_mix"] == {
        "text": 11,
        "table": 22,
        "latex": 67,
    }
    assert production_cfg["layout"]["occupancy"]["whitespace_strategy"] == "compact"
    assert production_cfg["layout"]["occupancy"]["max_place_attempts"] == 120


@pytest.mark.integration
def test_invalid_missing_config_path_fails_safely(tmp_path: Path):
    missing = tmp_path / "missing.yaml"

    with pytest.raises(Exception):
        load_config(str(missing))