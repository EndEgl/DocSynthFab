# test/integration/test_architecture_gui_backend_config_contract.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - PyYAML>=6.0,<7.0

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from docsynthfab.orchestrator import RunOrchestrator, RunRequest


@pytest.mark.integration
def test_architecture_preview_config_and_production_config_are_identical(
    default_config_path: Path,
    tmp_path: Path,
):
    """
    Architecture digital twin contract:

    Effective YAML preview and production run config must use the same merge
    semantics. A value visible in the GUI preview must be the value used by
    the generator.
    """
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

    # Raw YAML is the last user-level override layer.
    assert production_cfg["content"]["block_mix"] == {
        "text": 11,
        "table": 22,
        "latex": 67,
    }
    assert production_cfg["layout"]["occupancy"]["whitespace_strategy"] == "compact"

    # Dot-path override not touched by raw YAML must survive.
    assert production_cfg["layout"]["occupancy"]["max_place_attempts"] == 120


@pytest.mark.integration
def test_architecture_run_request_to_effective_config_preserves_backend_contract(
    default_config_path: Path,
    tmp_path: Path,
):
    """
    RunRequest is the backend boundary. Every runtime field and GUI override
    must survive into the effective config before generation starts.
    """
    orch = RunOrchestrator()

    req = RunRequest(
        config_path=str(default_config_path),
        out_root=str(tmp_path / "runtime_contract_out"),
        pages=4,
        workers=1,
        seed=20260527,
        smoke_test=False,
        export_targets=["native"],
        overrides={
            "content.block_mix": {"text": 100, "table": 0, "latex": 0},
            "content.source_mode": "random_chars",
            "content.text_mode": "chars",
            "layout.occupancy.enable": True,
            "layout.occupancy.whitespace_strategy": "spread",
            "layout.occupancy.max_place_attempts": 150,
        },
        raw_yaml_override_text="""
layout:
  occupancy:
    whitespace_strategy: compact
""",
    )

    cfg = orch.build_effective_config_dict(req)

    assert cfg["io"]["out_root"] == str(tmp_path / "runtime_contract_out")
    assert cfg["run"]["pages"] == 4
    assert cfg["run"]["workers"] == 1
    assert cfg["run"]["seed"] == 20260527
    assert cfg["run"]["export_targets"] == ["native"]

    assert cfg["content"]["block_mix"] == {
        "text": 100,
        "table": 0,
        "latex": 0,
    }
    assert cfg["content"]["source_mode"] == "random_chars"
    assert cfg["content"]["text_mode"] == "chars"

    assert cfg["layout"]["occupancy"]["enable"] is True
    assert cfg["layout"]["occupancy"]["whitespace_strategy"] == "compact"
    assert cfg["layout"]["occupancy"]["max_place_attempts"] == 150



