from __future__ import annotations

import random

from docsynthfab.layout.line_gap import (
    _apply_line_gap_randomness,
    _sample_distribution_scale,
    resolve_line_gap_policy,
)


def test_resolve_line_gap_policy_uses_explicit_policy_and_clamps_percent():
    policy = resolve_line_gap_policy(
        {
            "line_gap": {
                "distribution": "uniform",
                "randomness_percent": 150,
                "min_scale": 0.8,
                "max_scale": 1.4,
                "mean_ratio": 2.0,
                "std_ratio": 0.0,
                "exponential_lambda": 0.0,
            }
        }
    )

    assert policy["distribution"] == "uniform"
    assert policy["randomness_percent"] == 100.0
    assert policy["min_scale"] == 0.8
    assert policy["max_scale"] == 1.4
    assert policy["mean_ratio"] == 1.0
    assert policy["std_ratio"] == 0.01
    assert policy["exponential_lambda"] == 0.01


def test_resolve_line_gap_policy_falls_back_to_legacy_scale():
    policy = resolve_line_gap_policy({"line_gap_random_scale": 0.6})

    assert policy["distribution"] == "gaussian"
    assert 0.0 < policy["randomness_percent"] <= 100.0
    assert policy["min_scale"] < policy["max_scale"]


def test_sample_distribution_scale_zero_randomness_returns_one():
    scale = _sample_distribution_scale(
        policy={
            "distribution": "gaussian",
            "randomness_percent": 0,
            "min_scale": 0.5,
            "max_scale": 1.8,
        },
        rng=random.Random(123),
    )

    assert scale == 1.0


def test_sample_distribution_scale_supported_distributions_stay_in_bounds():
    for distribution in ["uniform", "exponential", "lognormal", "gaussian"]:
        policy = {
            "distribution": distribution,
            "randomness_percent": 75,
            "min_scale": 0.75,
            "max_scale": 1.35,
            "mean_ratio": 0.45,
            "std_ratio": 0.18,
            "exponential_lambda": 2.5,
        }

        for _ in range(50):
            scale = _sample_distribution_scale(
                policy=policy,
                rng=random.Random(123 + _),
            )

            assert 0.75 <= scale <= 1.35


def test_apply_line_gap_randomness_no_strength_returns_same_bbox():
    bbox = (100, 200, 300, 20)

    out = _apply_line_gap_randomness(
        bbox,
        block_y=180,
        block_h=300,
        line_index=2,
        line_count=8,
        line_h=30,
        scale=0.0,
        policy=None,
        density_level="normal",
        block_type="paragraph",
        rng=random.Random(123),
    )

    assert out == bbox


def test_apply_line_gap_randomness_table_block_is_not_shifted():
    bbox = (100, 200, 300, 20)

    out = _apply_line_gap_randomness(
        bbox,
        block_y=180,
        block_h=300,
        line_index=2,
        line_count=8,
        line_h=30,
        policy={
            "distribution": "uniform",
            "randomness_percent": 100,
            "min_scale": 0.7,
            "max_scale": 1.5,
        },
        density_level="normal",
        block_type="table",
        rng=random.Random(123),
    )

    assert out == bbox


def test_apply_line_gap_randomness_keeps_bbox_inside_block():
    bbox = (100, 260, 300, 20)

    out = _apply_line_gap_randomness(
        bbox,
        block_y=180,
        block_h=300,
        line_index=4,
        line_count=10,
        line_h=32,
        policy={
            "distribution": "uniform",
            "randomness_percent": 100,
            "min_scale": 0.7,
            "max_scale": 1.5,
        },
        density_level="sparse",
        block_type="paragraph",
        rng=random.Random(999),
    )

    x, y, w, h = out

    assert x == bbox[0]
    assert w == bbox[2]
    assert h == bbox[3]
    assert 180 <= y <= 180 + 300 - h