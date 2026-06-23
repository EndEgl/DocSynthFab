# src/docsynthfab/layout/line_rebalance.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import List

from .specs import BlockSpec


def _rebalance_line_counts(
    blocks: List[BlockSpec],
    mins: List[int],
    desired: List[int],
    caps: List[int],
    target_total: int,
    rng: random.Random,
) -> List[int]:
    out = list(desired)
    current = sum(out)

    growable = [
        idx
        for idx, block in enumerate(blocks)
        if block.block_type in {"paragraph", "list", "equation"}
    ]
    shrinkable = [
        idx
        for idx, block in enumerate(blocks)
        if block.block_type in {"paragraph", "list", "equation"}
    ]

    guard = 0

    while current < target_total and guard < 200_000:
        guard += 1
        candidates = [idx for idx in growable if out[idx] < caps[idx]]

        if not candidates:
            break

        candidates.sort(
            key=lambda idx: (caps[idx] - out[idx], blocks[idx].bbox[3]),
            reverse=True,
        )
        top = candidates[: min(6, len(candidates))]
        pick = rng.choice(top)

        out[pick] += 1
        current += 1

    guard = 0

    while current > target_total and guard < 200_000:
        guard += 1
        candidates = [idx for idx in shrinkable if out[idx] > mins[idx]]

        if not candidates:
            break

        candidates.sort(
            key=lambda idx: (out[idx] - mins[idx], blocks[idx].bbox[3]),
            reverse=True,
        )
        top = candidates[: min(6, len(candidates))]
        pick = rng.choice(top)

        out[pick] -= 1
        current -= 1

    return out



