# src/ai1_gen/augment/quality.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np


def quick_quality_gate(
    before_mt: np.ndarray,
    before_mm: np.ndarray,
    after_mt: np.ndarray,
    after_mm: np.ndarray,
    meta: Dict[str, Any],
) -> Tuple[bool, Dict[str, float]]:
    bt = max(1, int(np.count_nonzero(before_mt)))
    at = int(np.count_nonzero(after_mt))

    bm = int(np.count_nonzero(before_mm))
    am = int(np.count_nonzero(after_mm))

    text_ratio = at / bt
    math_ratio = 1.0 if bm == 0 else (am / max(1, bm))

    has_equation = bool(meta.get("has_equation", False))
    ok = text_ratio >= 0.72 and (not has_equation or math_ratio >= 0.82)

    return ok, {
        "text_area_ratio": float(text_ratio),
        "math_area_ratio": float(math_ratio),
        "before_text_nz": float(bt),
        "after_text_nz": float(at),
        "before_math_nz": float(bm),
        "after_math_nz": float(am),
    }


def sync_meta_from_annotation_and_masks(
    ann: Dict[str, Any],
    mt: np.ndarray,
    mm: np.ndarray,
) -> None:
    meta = ann.setdefault("meta", {})
    lines = ann.get("lines", []) or []
    blocks = ann.get("blocks", []) or []

    has_math_line = any(str(ln.get("line_type", "")) == "math" for ln in lines)
    has_table_block = any(str(b.get("block_type", "")) == "table" for b in blocks)
    has_figure_block = any(str(b.get("block_type", "")) == "figure" for b in blocks)

    meta["has_equation"] = bool(has_math_line and np.any(mm > 0))
    meta["has_table"] = bool(has_table_block)
    meta["has_figure"] = bool(has_figure_block)
    meta["mask_text_nonzero"] = int(np.count_nonzero(mt))
    meta["mask_math_nonzero"] = int(np.count_nonzero(mm))