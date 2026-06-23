from __future__ import annotations

from pathlib import Path

import pytest

from docsynthfab.config import AppConfig, load_config
from docsynthfab.orchestrator import RunOrchestrator


@pytest.mark.integration
def test_default_config_loads_as_app_config(default_config_path: Path):
    cfg = load_config(str(default_config_path))

    assert isinstance(cfg, AppConfig)
    assert cfg.pages > 0
    assert cfg.workers > 0
    assert isinstance(cfg.raw, dict)


@pytest.mark.integration
def test_orchestrator_builds_config_with_dot_path_overrides(default_config_path: Path):
    orch = RunOrchestrator()

    cfg = orch.build_config_with_user_override(
        config_path=str(default_config_path),
        overrides={
            "run.pages": 3,
            "run.workers": 1,
            "run.seed": 777,
            "content.block_mix": {"text": 100, "table": 0, "latex": 0},
        },
        raw_yaml_override_text=None,
    )

    assert cfg["run"]["pages"] == 3
    assert cfg["run"]["workers"] == 1
    assert cfg["run"]["seed"] == 777
    assert cfg["content"]["block_mix"]["text"] == 100


@pytest.mark.integration
def test_orchestrator_effective_yaml_preview_contains_runtime_overrides(default_config_path: Path, tmp_path: Path):
    orch = RunOrchestrator()

    text = orch.build_effective_config_yaml_text(
        config_path=str(default_config_path),
        overrides={"content.block_mix": {"text": 100, "table": 0, "latex": 0}},
        raw_yaml_override_text=None,
        out_root=str(tmp_path / "out"),
        pages=5,
        workers=1,
        seed=42,
        smoke_test=False,
    )

    assert "pages" in text
    assert "workers" in text
    assert "seed" in text
    assert "block_mix" in text


@pytest.mark.integration
def test_invalid_missing_config_path_fails_safely(tmp_path: Path):
    missing = tmp_path / "missing.yaml"

    with pytest.raises(Exception):
        load_config(str(missing))



