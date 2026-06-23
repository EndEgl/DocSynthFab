# test/e2e/test_12_cli_web_effective_config_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9

from __future__ import annotations

from pathlib import Path

import pytest

from docsynthfab.orchestrator import RunOrchestrator

from e2e_support import (
    assert_no_fatal_log_errors,
    assert_output_package_exists,
    assert_page_counts_match,
    fresh_output_dir,
    read_text_safe,
    run_cli_generation,
)


@pytest.mark.e2e
@pytest.mark.slow
def test_cli_accepts_web_style_effective_config_and_generates_images(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "cli_web_effective_config")

    orch = RunOrchestrator()

    effective_yaml = orch.build_effective_config_yaml_text(
        config_path=str(e2e_default_config),
        overrides={
            "run.export_targets": ["native"],
            "content.block_mix": {"text": 100, "table": 0, "latex": 0},
            "content.source_mode": "random_chars",
            "content.text_mode": "chars",
            "latex.enable": False,
            "render.latex": False,
            "augment.enable": False,
            "layout.occupancy.enable": True,
            "layout.occupancy.whitespace_strategy": "balanced",
            "layout.occupancy.max_place_attempts": 48,
            "telemetry.temperature.require_temp_sensor": False,
        },
        raw_yaml_override_text="",
        out_root=str(out_root),
        pages=1,
        workers=1,
        seed=20260529,
        smoke_test=False,
        export_targets=["native"],
    )

    effective_config = out_root / "web_style_effective_config.yaml"
    effective_config.write_text(effective_yaml, encoding="utf-8")

    result = run_cli_generation(
        project_root=project_root,
        config_path=effective_config,
        out_root=out_root,
        pages=1,
        workers=1,
        seed=20260529,
        export="native",
        timeout_s=180.0,
    )

    assert result.returncode == 0, {
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
        "run_log": read_text_safe(out_root / "run.log")[-4000:],
        "errors": read_text_safe(out_root / "errors.jsonl")[-4000:],
        "failed": read_text_safe(out_root / "failed_pages.log")[-4000:],
        "effective_config": effective_yaml[-4000:],
    }

    assert_output_package_exists(out_root)
    counts = assert_page_counts_match(out_root, expected_pages=1)
    assert counts["image_count"] == 1
    assert_no_fatal_log_errors(out_root)



