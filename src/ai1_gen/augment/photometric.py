# src/ai1_gen/augment/photometric.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - opencv-python>=4.8,<5.0

from __future__ import annotations

import random
from typing import Any, Dict, List

import cv2
import numpy as np


def apply_photometric(
    img: np.ndarray,
    rng: random.Random,
    cfg: Dict[str, Any],
    trace: List[Dict[str, Any]],
) -> np.ndarray:
    g0, g1 = cfg.get("gamma", [0.75, 1.25])
    gamma = rng.uniform(float(g0), float(g1))
    inv = 1.0 / max(1e-6, gamma)

    lut = np.array(
        [(i / 255.0) ** inv * 255.0 for i in range(256)],
        dtype=np.uint8,
    )
    out = cv2.LUT(img, lut)

    b0, b1 = cfg.get("brightness", [-20, 20])
    c0, c1 = cfg.get("contrast", [0.85, 1.20])
    beta = rng.uniform(float(b0), float(b1))
    alpha = rng.uniform(float(c0), float(c1))

    out = cv2.convertScaleAbs(out, alpha=alpha, beta=beta)

    trace.append(
        {
            "op": "photometric",
            "gamma": gamma,
            "alpha": alpha,
            "beta": beta,
        }
    )

    return out