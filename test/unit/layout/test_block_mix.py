from __future__ import annotations

import random

from docsynthfab.layout.block_mix import (
    make_block_mix_sequence,
    normalize_block_mix,
    sample_block_kind_from_mix,
    text_block_type_for_mix,
)


def test_normalize_block_mix_normalizes_percent_values():
    out = normalize_block_mix(
        {
            "block_mix": {
                "text": 60,
                "table": 30,
                "latex": 10,
            }
        }
    )

    assert round(sum(out.values()), 6) == 1.0
    assert out["text"] == 0.6
    assert out["table"] == 0.3
    assert out["latex"] == 0.1


def test_normalize_block_mix_uses_defaults_when_total_is_zero():
    out = normalize_block_mix(
        {
            "block_mix": {
                "text": 0,
                "table": 0,
                "latex": 0,
            }
        }
    )

    assert round(sum(out.values()), 6) == 1.0
    assert round(out["text"], 2) == 0.60
    assert round(out["table"], 2) == 0.25
    assert round(out["latex"], 2) == 0.15


def test_normalize_block_mix_handles_invalid_block_mix_shape():
    out = normalize_block_mix({"block_mix": "bad"})

    assert round(sum(out.values()), 6) == 1.0
    assert set(out) == {"text", "table", "latex"}


def test_sample_block_kind_from_mix_falls_back_to_text_when_empty():
    assert sample_block_kind_from_mix(random.Random(123), {}) == "text"
    assert sample_block_kind_from_mix(
        random.Random(123),
        {"text": 0.0, "table": 0.0, "latex": 0.0},
    ) == "text"


def test_text_block_type_for_mix_returns_title_only_for_first_allowed_block():
    rng = random.Random(123)

    assert text_block_type_for_mix(rng, index=0, allow_title=True) == "title"
    assert text_block_type_for_mix(rng, index=1, allow_title=True) in {
        "paragraph",
        "list",
    }
    assert text_block_type_for_mix(rng, index=0, allow_title=False) in {
        "paragraph",
        "list",
    }


def test_make_block_mix_sequence_table_only():
    seq = make_block_mix_sequence(
        random.Random(123),
        block_budget=5,
        block_mix={"text": 0.0, "table": 1.0, "latex": 0.0},
    )

    assert seq == ["table", "table", "table", "table", "table"]


def test_make_block_mix_sequence_latex_only():
    seq = make_block_mix_sequence(
        random.Random(123),
        block_budget=4,
        block_mix={"text": 0.0, "table": 0.0, "latex": 1.0},
    )

    assert seq == ["equation", "equation", "equation", "equation"]


def test_make_block_mix_sequence_text_only_uses_title_when_budget_allows():
    seq = make_block_mix_sequence(
        random.Random(123),
        block_budget=4,
        block_mix={"text": 1.0, "table": 0.0, "latex": 0.0},
    )

    assert len(seq) == 4
    assert seq[0] == "title"
    assert set(seq[1:]).issubset({"paragraph", "list"})


def test_make_block_mix_sequence_mixed_forces_present_categories():
    seq = make_block_mix_sequence(
        random.Random(456),
        block_budget=8,
        block_mix={"text": 1.0, "table": 1.0, "latex": 1.0},
    )

    assert len(seq) == 8
    assert "table" in seq
    assert "equation" in seq
    assert any(item in {"title", "paragraph", "list"} for item in seq)


def test_make_block_mix_sequence_clamps_non_positive_budget_to_one():
    seq = make_block_mix_sequence(
        random.Random(123),
        block_budget=0,
        block_mix={"text": 1.0, "table": 0.0, "latex": 0.0},
    )

    assert len(seq) == 1