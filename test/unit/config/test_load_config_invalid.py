import pytest

from ai1_gen.config import ConfigError, load_config


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