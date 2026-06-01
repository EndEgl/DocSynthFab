# test/unit/config/test_config.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - PyYAML>=6.0,<7.0

from __future__ import annotations

from pathlib import Path

import pytest

import ai1_gen.config as config_pkg
from ai1_gen.config import (
    AppConfig,
    ConfigError,
    _get,
    _norm_dist,
    get_nested,
    load_config,
    normalize_distribution,
)


def _minimal_valid_yaml() -> str:
    return """
version: ai1-ds-v1.3.2
io:
  out_root: out
run:
  pages: 4
  workers: 1
  seed: 123
  splits:
    train: 0.8
    val: 0.1
    test: 0.1
qc:
  mask_binary_required: true
  overlap_text_over_math_max_ratio: 0.01
  require_global_line_order_contiguous: true
thresholds: {}
augment:
  enable: false
telemetry:
  mode: single_line
  ascii_only: true
  show_eta: true
  show_rate: true
  update_interval_s: 1.2
  temperature:
    require_temp_sensor: false
    prefer_gpu: true
    """.strip()


def test_config_is_package_after_modularization():
    """
    Config is now:
      src/ai1_gen/config/

    The old file:
      src/ai1_gen/config.py

    must not exist anymore because it conflicts with the package.
    """
    package_init = Path(config_pkg.__file__).resolve()
    package_dir = package_init.parent
    old_file = package_dir.parent / "config.py"

    assert package_init.name == "__init__.py"
    assert package_dir.name == "config"
    assert package_dir.is_dir()

    assert (package_dir / "config.py").exists()
    assert (package_dir / "loader.py").exists()
    assert (package_dir / "helpers.py").exists()
    assert (package_dir / "errors.py").exists()

    assert not old_file.exists(), (
        "Old src/ai1_gen/config.py still exists. "
        "It conflicts with the new ai1_gen.config package."
    )


def test_config_public_exports_contract():
    expected = {
        "AppConfig",
        "ConfigError",
        "load_config",
        "_get",
        "_norm_dist",
        "get_nested",
        "normalize_distribution",
    }

    assert expected <= set(config_pkg.__all__)

    for name in expected:
        assert hasattr(config_pkg, name), f"ai1_gen.config missing public export: {name}"


def test_load_config_reads_minimal_valid_yaml(tmp_path):
    cfg_path = tmp_path / "minimal_valid.yaml"
    cfg_path.write_text(_minimal_valid_yaml(), encoding="utf-8")

    cfg = load_config(str(cfg_path))

    assert isinstance(cfg, AppConfig)
    assert hasattr(cfg, "raw")
    assert hasattr(cfg, "pages")
    assert hasattr(cfg, "workers")
    assert hasattr(cfg, "seed")

    assert cfg.pages == 4
    assert cfg.workers == 1
    assert cfg.seed == 123


def test_load_config_rejects_missing_run_section(tmp_path):
    cfg_path = tmp_path / "invalid_missing_run.yaml"
    cfg_path.write_text(
        """
version: ai1-ds-v1.3.2
io:
  out_root: out
qc: {}
thresholds: {}
augment:
  enable: false
telemetry: {}
        """.strip(),
        encoding="utf-8",
    )

    with pytest.raises((ConfigError, KeyError, ValueError, TypeError)):
        load_config(str(cfg_path))


def test_load_config_rejects_invalid_split_distribution(tmp_path):
    cfg_path = tmp_path / "invalid_bad_distribution.yaml"
    cfg_path.write_text(
        """
version: ai1-ds-v1.3.2
io:
  out_root: out
run:
  pages: 4
  workers: 1
  seed: 123
  splits:
    train: 0
    val: 0
    test: 0
qc: {}
thresholds: {}
augment:
  enable: false
telemetry: {}
        """.strip(),
        encoding="utf-8",
    )

    with pytest.raises((ConfigError, KeyError, ValueError, TypeError)):
        load_config(str(cfg_path))


def test_get_nested_reads_dot_path_and_default():
    data = {
        "a": {
            "b": {
                "c": 42,
            }
        }
    }

    assert get_nested(data, "a.b.c", "missing") == 42
    assert get_nested(data, "a.b.x", "missing") == "missing"


def test_private_get_keeps_backward_compatibility():
    data = {
        "run": {
            "pages": 10,
        }
    }

    assert _get(data, "run.pages", 0) == 10
    assert _get(data, "run.missing", 99) == 99


def test_normalize_distribution_normalizes_values():
    out = normalize_distribution(
        {
            "train": 8,
            "val": 1,
            "test": 1,
        },
        keys=("train", "val", "test"),
    )

    assert round(out["train"], 6) == 0.8
    assert round(out["val"], 6) == 0.1
    assert round(out["test"], 6) == 0.1
    assert round(sum(out.values()), 6) == 1.0


def test_norm_dist_keeps_backward_compatibility():
    out = _norm_dist(
        {
            "a": 2,
            "b": 2,
        },
        ["a", "b"],
    )

    assert out == {
        "a": 0.5,
        "b": 0.5,
    }