# src/docsynthfab/augment/common.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - opencv-python>=4.8,<5.0

from __future__ import annotations

import random
from typing import List, Tuple

import cv2
import numpy as np


def clip_bbox_xywh(b: List[int], w: int, h: int) -> List[int]:
    x, y, bw, bh = (int(b[0]), int(b[1]), int(b[2]), int(b[3]))
    x = max(0, min(x, w - 1))
    y = max(0, min(y, h - 1))
    bw = max(0, min(bw, w - x))
    bh = max(0, min(bh, h - y))
    return [x, y, bw, bh]


def bbox_area(b: List[int]) -> int:
    return int(b[2]) * int(b[3])


def warp(image: np.ndarray, M: np.ndarray, out_wh: Tuple[int, int], is_mask: bool) -> np.ndarray:
    ow, oh = out_wh
    interp = cv2.INTER_NEAREST if is_mask else cv2.INTER_LINEAR
    border = (255, 255, 255) if image.ndim == 3 else 0

    return cv2.warpPerspective(
        image,
        M,
        (ow, oh),
        flags=interp,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border,
    )


def np_rng_from_rng(rng: random.Random) -> np.random.Generator:
    return np.random.default_rng(rng.randint(0, 2**32 - 1))



