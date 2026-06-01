# src/ai1_gen/augment/result.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class AugResult:
    image_aug_u8: np.ndarray
    mask_text_aug_u8: np.ndarray
    mask_math_aug_u8: np.ndarray
    ann_aug: Dict[str, Any]
    aug_trace: List[Dict[str, Any]]
    geom_M: Optional[np.ndarray]