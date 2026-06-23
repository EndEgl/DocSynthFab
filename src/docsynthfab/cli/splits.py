# src/docsynthfab/cli/splits.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import Any, Dict, Tuple


def normalized_split_ratios(run_cfg: Dict[str, Any]) -> Tuple[float, float, float]:
    splits = run_cfg.get("splits", {}) or {}

    tr = float(splits.get("train", 0.80))
    va = float(splits.get("val", 0.10))
    te = float(splits.get("test", 0.10))

    total = tr + va + te

    if total <= 0:
        return 0.80, 0.10, 0.10

    return tr / total, va / total, te / total


def split_of(i: int, n: int, run_cfg: Dict[str, Any]) -> str:
    train_r, val_r, _ = normalized_split_ratios(run_cfg)
    r = i / max(1, n)

    if r < train_r:
        return "train"

    if r < train_r + val_r:
        return "val"

    return "test"


_normalized_split_ratios = normalized_split_ratios
_split_of = split_of



