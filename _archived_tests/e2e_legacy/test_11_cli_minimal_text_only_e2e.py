# test/e2e/test_11_cli_minimal_text_only_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - PyYAML>=6.0,<7.0

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

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
def test_cli_minimal_text_only_generates_one_image(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(e2e_out_root / "cli_minimal_text_only")

    # Build a small effective config from default.yaml.
    cfg = yaml.safe_load(e2e_default_config.read_text(encoding="utf-8"))

    cfg.setdefault("content", {})
    cfg["content"]["block_mix"] = {"text": 100, "table": 0, "latex": 0}
    cfg["content"]["source_mode"] = "random_chars"
    cfg["content"]["text_mode"] = "chars"

    cfg.setdefault("latex", {})
    cfg["latex"]["enable"] = False

    cfg.setdefault("render", {})
    cfg["render"]["latex"] = False

    cfg.setdefault("augment", {})
    cfg["augment"]["enable"] = False

    cfg.setdefault("run", {})
    cfg["run"]["export_targets"] = ["native"]
    cfg["run"]["fail_fast"] = True
    cfg["run"]["max_fail_ratio"] = 1.0

    cfg.setdefault("telemetry", {})
    cfg["telemetry"]["mode"] = "single_line"
    cfg["telemetry"]["temperature"] = {
        "require_temp_sensor": False,
        "prefer_gpu": True,
    }

    effective_config = out_root / "cli_minimal_text_only.yaml"
    effective_config.write_text(
        yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

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
    }

    assert_output_package_exists(out_root)
    counts = assert_page_counts_match(out_root, expected_pages=1)
    assert counts["image_count"] == 1
    assert_no_fatal_log_errors(out_root)



