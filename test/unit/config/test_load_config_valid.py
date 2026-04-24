from pathlib import Path

from ai1_gen.config import load_config


def test_load_config_reads_minimal_valid_yaml(tmp_path):
    cfg_path = tmp_path / "minimal_valid.yaml"
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
        """.strip(),
        encoding="utf-8",
    )

    cfg = load_config(str(cfg_path))

    assert cfg is not None
    assert hasattr(cfg, "raw")
    assert hasattr(cfg, "pages")
    assert hasattr(cfg, "workers")
    assert hasattr(cfg, "seed")