# test/e2e/test_09_backend_parameter_reaches_output_e2e.py
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
    fresh_output_dir,
    load_ann_gt_pairs,
    run_backend_generation,
)


@pytest.mark.e2e
@pytest.mark.slow
def test_backend_gui_style_parameters_reach_effective_config_and_output(
    e2e_default_config: Path,
    e2e_out_root: Path,
):
    out_root = fresh_output_dir(
        e2e_out_root / "backend_gui_style_parameters_reach_output"
    )

    orch, run_id, status = run_backend_generation(
        config_path=e2e_default_config,
        out_root=out_root,
        pages=4,
        workers=1,
        seed=20260527,
        timeout_s=300.0,
        overrides={
            "run.export_targets": ["native"],
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

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    effective_path = orch.work_root / run_id / "effective_config.yaml"
    assert effective_path.exists()

    cfg = yaml.safe_load(effective_path.read_text(encoding="utf-8"))

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

    assert_output_package_exists(out_root)
    assert_no_fatal_log_errors(out_root)

    pairs = load_ann_gt_pairs(out_root)
    assert pairs

    table_like_blocks = 0
    math_like_lines = 0

    for _ann_path, ann, _gt_path, _gt in pairs:
        for block in ann.get("blocks", []) or []:
            block_type = str(block.get("block_type", "")).lower()
            if "table" in block_type:
                table_like_blocks += 1

        for line in ann.get("lines", []) or []:
            line_type = str(line.get("line_type", "")).lower()
            if line_type in {"math", "latex", "equation"}:
                math_like_lines += 1

    assert table_like_blocks == 0
    assert math_like_lines == 0