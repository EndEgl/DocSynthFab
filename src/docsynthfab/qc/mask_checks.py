# src/docsynthfab/qc/mask_checks.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

import numpy as np


def _is_binary_u8(mask: np.ndarray) -> bool:
    """Return True when the mask is uint8 and contains only 0 or 255 values."""
    if mask.dtype != np.uint8:
        return False

    return bool(np.all((mask == 0) | (mask == 255)))


def _visual_content_ratio(
    mask_text: np.ndarray,
    mask_math: np.ndarray,
) -> float:
    """Return the ratio of visible text-or-math pixels over the full page area."""
    h, w = mask_text.shape[:2]
    content = np.logical_or(mask_text > 0, mask_math > 0)

    return float(np.count_nonzero(content)) / float(max(1, h * w))



