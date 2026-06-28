# test/unit/config/test_config.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - PyYAML>=6.0,<7.0

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import docsynthfab.config as config_pkg
from docsynthfab.config import (
    AppConfig,
    ConfigError,
    _get,
    _norm_dist,
    get_nested,
    load_config,
    normalize_distribution,
)
from docsynthfab.config.schema import validate_config_raw


def _minimal_valid_raw() -> dict:
    return {
        "project": {
            "version": "docsynthfab-ds-v0.1",
        },
        "io": {
            "out_root": "out",
            "tmp_dir": "_tmp",
        },
        "run": {
            "pages": 4,
            "workers": 1,
            "seed": 123,
            "splits": {
                "train": 0.8,
                "val": 0.1,
                "test": 0.1,
            },
        },
        "dist": {
            "density_dist": {
                "sparse": 1,
                "normal": 2,
                "dense": 1,
            },
            "scale_dist": {
                "dpi200": 1,
                "dpi300": 3,
            },
            "noise_level_dist": {
                "clean": 3,
                "medium": 5,
                "heavy": 2,
            },
        },
        "page": {
            "default_size": "a4_portrait",
            "dpi_choices": [200, 300],
            "size_dist": {
                "a4_portrait": 6,
                "letter_portrait": 2,
                "a4_landscape": 1,
                "letter_landscape": 1,
            },
        },
        "layout": {
            "targets": {
                "sparse": {
                    "line_count_range": [10, 20],
                    "block_count_range": [2, 5],
                },
                "normal": {
                    "line_count_range": [20, 60],
                    "block_count_range": [5, 15],
                },
            },
        },
        "density_thresholds": {
            "active": True,
        },
        "thresholds": {
            "legacy": True,
        },
        "qc": {
            "dist_tolerance_abs": 0.04,
            "mask_binary_required": True,
        },
        "augment": {
            "enable": False,
        },
        "render": {
            "text": {
                "enabled": True,
            },
        },
        "telemetry": {
            "mode": "single_line",
            "ascii_only": True,
            "show_eta": True,
            "show_rate": True,
            "update_interval_s": 1.2,
            "temperature": {
                "require_temp_sensor": False,
                "prefer_gpu": True,
            },
        },
    }


def _minimal_valid_yaml() -> str:
    return """
project:
  version: docsynthfab-ds-v0.1
io:
  out_root: out
  tmp_dir: _tmp
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
  dist_tolerance_abs: 0.04
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


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


# ======================================================================================
# package contract
# ======================================================================================

def test_config_is_package_after_modularization():
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
        "Old src/docsynthfab/config.py still exists. "
        "It conflicts with the new docsynthfab.config package."
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
        assert hasattr(config_pkg, name), f"docsynthfab.config missing public export: {name}"


# ======================================================================================
# loader.py
# ======================================================================================

def test_load_config_reads_minimal_valid_yaml(tmp_path: Path):
    cfg_path = _write_text(tmp_path / "minimal_valid.yaml", _minimal_valid_yaml())

    cfg = load_config(str(cfg_path))

    assert isinstance(cfg, AppConfig)
    assert cfg.raw["run"]["pages"] == 4
    assert cfg.pages == 4
    assert cfg.workers == 1
    assert cfg.seed == 123
    assert cfg.out_root == "out"
    assert cfg.tmp_dir_name == "_tmp"


def test_load_config_rejects_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.yaml")


def test_load_config_rejects_non_dict_yaml(tmp_path: Path):
    cfg_path = _write_text(
        tmp_path / "list.yaml",
        """
- a
- b
        """,
    )

    with pytest.raises(ConfigError, match="cfg/invalid-yaml"):
        load_config(cfg_path)


def test_load_config_rejects_missing_run_section(tmp_path: Path):
    cfg_path = _write_text(
        tmp_path / "missing_run.yaml",
        """
project:
  version: docsynthfab-ds-v0.1
io:
  out_root: out
qc: {}
thresholds: {}
augment:
  enable: false
telemetry: {}
        """,
    )

    with pytest.raises(ConfigError, match="cfg/missing-run-section"):
        load_config(cfg_path)


def test_load_config_rejects_empty_run_section(tmp_path: Path):
    cfg_path = _write_text(
        tmp_path / "empty_run.yaml",
        """
run: {}
        """,
    )

    with pytest.raises(ConfigError, match="cfg/missing-run-section"):
        load_config(cfg_path)



@pytest.mark.parametrize(
    "splits",
    [
        {"train": 0, "val": 0, "test": 0},
        {"train": -1, "val": 1, "test": 1},
        {"train": "bad", "val": 1, "test": 1},
        {},
    ],
)
def test_load_config_rejects_invalid_split_distribution(
    tmp_path: Path,
    splits,
):
    cfg_path = tmp_path / "invalid_split.yaml"

    cfg_path.write_text(
        yaml.safe_dump(
            {
                "run": {
                    "pages": 4,
                    "workers": 1,
                    "seed": 123,
                    "splits": splits,
                }
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="cfg/invalid-split-distribution"):
        load_config(cfg_path)


# ======================================================================================
# helpers.py
# ======================================================================================

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
    assert _get({}, "run.pages", 123) == 123
    assert _get({"run": None}, "run.pages", 123) == 123


def test_norm_dist_normalizes_values():
    out = _norm_dist(
        {
            "a": 2,
            "b": 2,
        },
        "cfg/test-error",
    )

    assert out == {
        "a": 0.5,
        "b": 0.5,
    }


@pytest.mark.parametrize(
    "bad_dist",
    [
        {},
        [],
        {"a": 0, "b": 0},
        {"a": -1, "b": 2},
        {"a": "bad", "b": 2},
    ],
)
def test_norm_dist_rejects_invalid_distribution(bad_dist):
    with pytest.raises(ConfigError, match="cfg/test-error"):
        _norm_dist(bad_dist, "cfg/test-error")


def test_normalize_distribution_normalizes_values_and_keeps_requested_keys():
    out = normalize_distribution(
        {
            "train": 8,
            "val": 1,
            "test": 1,
            "extra": 10,
        },
        keys=("train", "val", "test", "missing"),
    )

    assert round(out["train"], 6) == 0.4
    assert round(out["val"], 6) == 0.05
    assert round(out["test"], 6) == 0.05
    assert out["missing"] == 0.0


def test_normalize_distribution_without_keys_returns_all_normalized_values():
    out = normalize_distribution(
        {
            "a": 1,
            "b": 3,
        }
    )

    assert out == {
        "a": 0.25,
        "b": 0.75,
    }


# ======================================================================================
# config.py / AppConfig
# ======================================================================================

def test_app_config_reads_core_properties():
    cfg = AppConfig(_minimal_valid_raw())

    assert cfg.version == "docsynthfab-ds-v0.1"
    assert cfg.out_root == "out"
    assert cfg.tmp_dir_name == "_tmp"
    assert cfg.pages == 4
    assert cfg.workers == 1
    assert cfg.seed == 123


def test_app_config_uses_defaults_when_optional_values_missing():
    cfg = AppConfig(
        {
            "run": {},
        }
    )

    assert cfg.version == "docsynthfab-ds-v0.1"
    assert cfg.out_root == "out/default_run"
    assert cfg.tmp_dir_name == "_tmp"
    assert cfg.pages == 3000
    assert cfg.workers == 6
    assert cfg.seed == 1337
    assert cfg.default_page_size() == "a4_portrait"
    assert cfg.dpi_choices() == (200, 300)
    assert cfg.dist_tolerance_abs() == 0.03


def test_app_config_distribution_methods_normalize_configured_distributions():
    cfg = AppConfig(_minimal_valid_raw())

    density = cfg.density_dist()
    scale = cfg.scale_dist()
    noise = cfg.noise_dist()
    page_size = cfg.page_size_dist()

    assert round(sum(density.values()), 6) == 1.0
    assert density["normal"] == 0.5

    assert round(sum(scale.values()), 6) == 1.0
    assert scale["dpi300"] == 0.75

    assert round(sum(noise.values()), 6) == 1.0
    assert noise["medium"] == 0.5

    assert round(sum(page_size.values()), 6) == 1.0
    assert page_size["a4_portrait"] == 0.6


def test_app_config_noise_and_page_size_have_defaults():
    cfg = AppConfig(
        {
            "run": {},
        }
    )

    noise = cfg.noise_dist()
    page_size = cfg.page_size_dist()

    assert round(sum(noise.values()), 6) == 1.0
    assert set(noise) == {"clean", "medium", "heavy"}

    assert round(sum(page_size.values()), 6) == 1.0
    assert "a4_portrait" in page_size
    assert "letter_portrait" in page_size


def test_app_config_density_and_scale_dist_require_configured_values():
    cfg = AppConfig(
        {
            "run": {},
        }
    )

    with pytest.raises(ConfigError, match="cfg/invalid-density-dist"):
        cfg.density_dist()

    with pytest.raises(ConfigError, match="cfg/invalid-scale-dist"):
        cfg.scale_dist()


def test_app_config_dpi_choices_and_default_page_size():
    cfg = AppConfig(_minimal_valid_raw())

    assert cfg.dpi_choices() == (200, 300)
    assert cfg.default_page_size() == "a4_portrait"


def test_app_config_density_targets_converts_ranges_to_tuples():
    cfg = AppConfig(_minimal_valid_raw())

    targets = cfg.density_targets()

    assert targets["sparse"]["line_count_range"] == (10, 20)
    assert targets["sparse"]["block_count_range"] == (2, 5)
    assert targets["normal"]["line_count_range"] == (20, 60)
    assert targets["normal"]["block_count_range"] == (5, 15)


def test_app_config_density_targets_skips_non_dict_specs():
    raw = _minimal_valid_raw()
    raw["layout"]["targets"]["bad"] = "not-a-dict"

    cfg = AppConfig(raw)

    assert "bad" not in cfg.density_targets()


def test_app_config_thresholds_prefers_density_thresholds_when_present():
    cfg = AppConfig(_minimal_valid_raw())

    assert cfg.thresholds() == {
        "active": True,
    }


def test_app_config_thresholds_falls_back_to_legacy_thresholds():
    raw = _minimal_valid_raw()
    raw["density_thresholds"] = {}

    cfg = AppConfig(raw)

    assert cfg.thresholds() == {
        "legacy": True,
    }


def test_app_config_returns_sub_configs():
    cfg = AppConfig(_minimal_valid_raw())

    assert cfg.telemetry()["mode"] == "single_line"
    assert cfg.augment()["enable"] is False
    assert cfg.render()["text"]["enabled"] is True
    assert cfg.qc()["mask_binary_required"] is True
    assert cfg.dist_tolerance_abs() == 0.04


# ======================================================================================
# schema.py
# ======================================================================================

def test_validate_config_raw_is_currently_noop_contract():
    assert validate_config_raw({}) is None
    assert validate_config_raw(_minimal_valid_raw()) is None