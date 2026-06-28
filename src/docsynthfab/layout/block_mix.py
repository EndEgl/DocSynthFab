# src/docsynthfab/layout/block_mix.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import Dict, List


TEXT_BLOCK_TYPES = {"title", "paragraph", "list"}


def normalize_block_mix(content_cfg: Dict[str, object]) -> Dict[str, float]:
    """
    Normalize content.block_mix into 0.0-1.0 proportions.

    Expected config shape:
    content.block_mix:
      text: 60
      table: 25
      latex: 15

    Guarantees:
    - table=100 -> table-only sequence
    - latex=100 -> equation-only sequence
    - text=100  -> text-only sequence
    """
    raw = content_cfg.get("block_mix", {}) or {}

    if not isinstance(raw, dict):
        raw = {}

    def read_percent(name: str, default: float) -> float:
        try:
            return max(0.0, float(raw.get(name, default)))
        except Exception:
            return float(default)

    text = read_percent("text", 60.0)
    table = read_percent("table", 25.0)
    latex = read_percent("latex", 15.0)

    total = text + table + latex

    if total <= 0.0:
        text, table, latex = 60.0, 25.0, 15.0
        total = 100.0

    return {
        "text": text / total,
        "table": table / total,
        "latex": latex / total,
    }


def sample_block_kind_from_mix(
    rng: random.Random,
    block_mix: Dict[str, float],
) -> str:
    """Sample one high-level block kind from normalized block_mix."""
    text_p = float(block_mix.get("text", 0.0))
    table_p = float(block_mix.get("table", 0.0))
    latex_p = float(block_mix.get("latex", 0.0))

    total = text_p + table_p + latex_p

    if total <= 0.0:
        return "text"

    text_p /= total
    table_p /= total

    pick = rng.random()

    if pick < text_p:
        return "text"

    if pick < text_p + table_p:
        return "table"

    return "latex"


def text_block_type_for_mix(
    rng: random.Random,
    *,
    index: int,
    allow_title: bool,
) -> str:
    """Choose the concrete block type when the high-level kind is text."""
    if allow_title and index == 0:
        return "title"

    return rng.choice(["paragraph", "paragraph", "paragraph", "list"])


def make_block_mix_sequence(
    rng: random.Random,
    block_budget: int,
    block_mix: Dict[str, float],
) -> List[str]:
    """
    Create a block sequence directly from content.block_mix.

    The function does not use legacy has_table_prob / has_equation_prob logic.
    """
    block_budget = max(1, int(block_budget))

    text_p = float(block_mix.get("text", 0.0))
    table_p = float(block_mix.get("table", 0.0))
    latex_p = float(block_mix.get("latex", 0.0))

    total = text_p + table_p + latex_p

    if total <= 0.0:
        text_p, table_p, latex_p = 1.0, 0.0, 0.0
        total = 1.0

    text_p /= total
    table_p /= total
    latex_p /= total

    if table_p >= 0.999:
        return ["table" for _ in range(block_budget)]

    if latex_p >= 0.999:
        return ["equation" for _ in range(block_budget)]

    if text_p >= 0.999:
        if block_budget == 1:
            return ["paragraph"]

        return ["title"] + [
            rng.choice(["paragraph", "paragraph", "paragraph", "list"])
            for _ in range(block_budget - 1)
        ]

    sequence: List[str] = []
    used_text_title = False

    for index in range(block_budget):
        kind = sample_block_kind_from_mix(
            rng,
            {
                "text": text_p,
                "table": table_p,
                "latex": latex_p,
            },
        )

        if kind == "table":
            sequence.append("table")
            continue

        if kind == "latex":
            sequence.append("equation")
            continue

        block_type = text_block_type_for_mix(
            rng,
            index=index,
            allow_title=not used_text_title,
        )

        if block_type == "title":
            used_text_title = True

        sequence.append(block_type)

    def has_text_block(items: List[str]) -> bool:
        return any(item in TEXT_BLOCK_TYPES for item in items)

    def replace_last_non_required(target: str, protected: set[str]) -> None:
        for idx in range(len(sequence) - 1, -1, -1):
            if sequence[idx] not in protected:
                sequence[idx] = target
                return

        if sequence:
            sequence[-1] = target

    if table_p > 0.0 and "table" not in sequence:
        replace_last_non_required("table", protected={"equation"})

    if latex_p > 0.0 and "equation" not in sequence:
        replace_last_non_required("equation", protected={"table"})

    if text_p > 0.0 and not has_text_block(sequence):
        replace_last_non_required("paragraph", protected={"table", "equation"})

    return sequence[:block_budget]



