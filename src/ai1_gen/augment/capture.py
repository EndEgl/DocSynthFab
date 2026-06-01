# src/ai1_gen/augment/capture.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - opencv-python>=4.8,<5.0
# - Pillow>=10,<12

from __future__ import annotations

import io
import random
from typing import Any, Dict, List

import cv2
import numpy as np
from PIL import Image


def apply_capture_sim(
    img: np.ndarray,
    rng: random.Random,
    cfg: Dict[str, Any],
    noise_level: str,
    trace: List[Dict[str, Any]],
) -> np.ndarray:
    h, w = img.shape[:2]

    if rng.random() < 0.30 or noise_level == "heavy":
        factor_range = cfg.get("downscale_factor", [0.65, 0.85])
        factor = rng.uniform(float(factor_range[0]), float(factor_range[1]))

        dw = max(8, int(w * factor))
        dh = max(8, int(h * factor))

        small = cv2.resize(img, (dw, dh), interpolation=cv2.INTER_AREA)
        up = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)

        if noise_level == "heavy":
            q_range = cfg.get("jpeg_quality_heavy", [25, 70])
        else:
            q_range = cfg.get("jpeg_quality_clean_medium", [40, 90])

        q = int(rng.uniform(q_range[0], q_range[1]))

        pil = Image.fromarray(up)
        buf = io.BytesIO()
        pil.save(buf, format="JPEG", quality=q, optimize=False)
        buf.seek(0)

        pil2 = Image.open(buf).convert("RGB")
        out = np.array(pil2, dtype=np.uint8)

        trace.append(
            {
                "op": "capture_sim",
                "downscale_factor": factor,
                "jpeg_quality": q,
            }
        )

        return out

    return img