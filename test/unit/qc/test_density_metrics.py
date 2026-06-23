from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from docsynthfab.qc.density_metrics import (
    _apply_density_adjustments,
    _best_density_bucket,
    _eligible_mask_from_ann,
    _soft_in_range,
    compute_density_metrics,
    mixed_band_variance,
)


class Cfg:
    def __init__(self, qc_cfg: dict[str, Any] | None = None):
        self._qc = qc_cfg or {}

    def qc(self):
        return self._qc


def test_eligible_mask_excludes_figure_blocks_with_padding():
    ann = {
        "blocks": [
            {"block_type": "figure", "bbox": [20, 20, 20, 20]},
            {"block_type": "paragraph", "bbox": [60, 60, 20, 20]},
        ]
    }

    eligible = _eligible_mask_from_ann(
        ann,
        H=100,
        W=100,
        exclude_block_types=("figure",),
        pad_px=5,
    )

    assert eligible.dtype == bool
    assert eligible[25, 25] is False or bool(eligible[25, 25]) is False
    assert bool(eligible[70, 70]) is True


def test_compute_density_metrics_global_and_eligible_ratios():
    text = np.zeros((100, 100), dtype=np.uint8)
    math = np.zeros((100, 100), dtype=np.uint8)

    text[0:10, 0:10] = 255
    math[20:30, 20:30] = 255

    ann = {
        "blocks": [
            {"block_type": "figure", "bbox": [50, 50, 40, 40]},
        ]
    }

    metrics = compute_density_metrics(
        text,
        math,
        ann,
        Cfg(
            {
                "density": {
                    "use_eligible_area_excluding_figures": True,
                    "eligible_pad_px": 0,
                    "exclude_block_types": ["figure"],
                }
            }
        ),
    )

    assert metrics["ink_ratio_text"] == 0.01
    assert metrics["ink_ratio_math"] == 0.01
    assert metrics["ink_ratio_content"] == 0.02
    assert metrics["eligible_excluded_frac"] == pytest.approx(0.16)
    assert metrics["ink_ratio_content_eligible"] > metrics["ink_ratio_content"]


def test_compute_density_metrics_can_disable_eligible_exclusion():
    text = np.zeros((100, 100), dtype=np.uint8)
    math = np.zeros((100, 100), dtype=np.uint8)

    text[0:10, 0:10] = 255

    metrics = compute_density_metrics(
        text,
        math,
        {"blocks": [{"block_type": "figure", "bbox": [0, 0, 90, 90]}]},
        Cfg(
            {
                "density": {
                    "use_eligible_area_excluding_figures": False,
                }
            }
        ),
    )

    assert metrics["ink_ratio_text"] == metrics["ink_ratio_text_eligible"]
    assert metrics["eligible_excluded_frac"] == 0.0


def test_soft_in_range_uses_absolute_margin():
    assert _soft_in_range(0.099, 0.100, 0.200, margin_abs=0.002) is True
    assert _soft_in_range(0.097, 0.100, 0.200, margin_abs=0.002) is False
    assert _soft_in_range(0.201, 0.100, 0.200, margin_abs=0.002) is True


def test_best_density_bucket_returns_closest_accepted_bucket():
    ranges = {
        "sparse": [0.00, 0.02],
        "normal": [0.05, 0.15],
        "dense": [0.20, 0.40],
    }

    assert _best_density_bucket(0.011, ranges, margin_abs=0.001) == "sparse"
    assert _best_density_bucket(0.090, ranges, margin_abs=0.001) == "normal"
    assert _best_density_bucket(0.500, ranges, margin_abs=0.001) is None


def test_apply_density_adjustments_lowers_floor_for_figures_tables_and_equations():
    lo_adj, hi_adj, info = _apply_density_adjustments(
        "normal",
        0.10,
        0.30,
        meta={
            "has_figure": True,
            "has_table": True,
            "has_equation": True,
        },
        metrics={
            "eligible_excluded_frac": 0.20,
        },
        cfg=Cfg(
            {
                "density": {
                    "figure_lo_scale": 0.75,
                    "table_lo_scale": 0.85,
                    "equation_lo_scale": 0.85,
                    "excluded_area_lo_scale": 0.80,
                }
            }
        ),
    )

    assert lo_adj < 0.10
    assert hi_adj == 0.30
    assert info["scales"]["figure"] == 0.75
    assert info["scales"]["table"] == 0.85
    assert info["scales"]["equation"] == 0.85


def test_mixed_band_variance_zero_for_uniform_empty_mask():
    mask = np.zeros((100, 100), dtype=bool)

    assert mixed_band_variance(mask, bands=5) == 0.0


def test_mixed_band_variance_positive_for_non_uniform_bands():
    mask = np.zeros((100, 100), dtype=bool)
    mask[0:50, :] = True

    value = mixed_band_variance(mask, bands=4)

    assert value > 0.0