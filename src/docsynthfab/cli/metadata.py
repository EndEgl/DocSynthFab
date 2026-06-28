# src/docsynthfab/cli/metadata.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

from typing import Any, Dict

import numpy as np


def sync_ann_meta_from_masks(ann: Dict[str, Any], mt: np.ndarray, mm: np.ndarray) -> None:
    meta = ann.setdefault("meta", {})
    lines = ann.get("lines", []) or []
    blocks = ann.get("blocks", []) or []

    math_line_count = sum(1 for ln in lines if str(ln.get("line_type", "")) == "math")
    eq_block_count = sum(1 for b in blocks if str(b.get("block_type", "")) == "equation")
    table_block_count = sum(1 for b in blocks if str(b.get("block_type", "")) == "table")
    figure_block_count = sum(1 for b in blocks if str(b.get("block_type", "")) == "figure")

    mask_text_nonzero = int(np.count_nonzero(mt))
    mask_math_nonzero = int(np.count_nonzero(mm))

    meta["mask_text_nonzero"] = mask_text_nonzero
    meta["mask_math_nonzero"] = mask_math_nonzero
    meta["math_line_count"] = int(math_line_count)
    meta["equation_block_count"] = int(eq_block_count)
    meta["table_block_count"] = int(table_block_count)
    meta["figure_block_count"] = int(figure_block_count)

    meta["has_equation_layout"] = bool(math_line_count > 0 or eq_block_count > 0)
    meta["has_equation"] = bool((math_line_count > 0 or eq_block_count > 0) and mask_math_nonzero > 0)
    meta["has_table"] = bool(table_block_count > 0)
    meta["has_figure"] = bool(figure_block_count > 0)

    meta.setdefault("page_family", "report")


def attach_worker_debug_meta(
    ann: Dict[str, Any],
    ps: Any,
    mt: np.ndarray,
    mm: np.ndarray,
) -> None:
    meta = ann.setdefault("meta", {})
    ps_blocks = getattr(ps, "blocks", []) or []
    ps_lines = getattr(ps, "lines", []) or []

    meta["_worker_debug"] = {
        "ps_equation_blocks": int(sum(1 for b in ps_blocks if getattr(b, "block_type", "") == "equation")),
        "ps_table_blocks": int(sum(1 for b in ps_blocks if getattr(b, "block_type", "") == "table")),
        "ps_figure_blocks": int(sum(1 for b in ps_blocks if getattr(b, "block_type", "") == "figure")),
        "ps_math_lines": int(sum(1 for ln in ps_lines if getattr(ln, "line_type", "") == "math")),
        "ps_total_lines": int(len(ps_lines)),
        "mask_text_nonzero_pre_qc": int(np.count_nonzero(mt)),
        "mask_math_nonzero_pre_qc": int(np.count_nonzero(mm)),
    }


# Backward-compatible private aliases.
_sync_ann_meta_from_masks = sync_ann_meta_from_masks
_attach_worker_debug_meta = attach_worker_debug_meta



