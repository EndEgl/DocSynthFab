# src/docsynthfab/augment/degradation.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - opencv-python>=4.8,<5.0

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

from .common import np_rng_from_rng


def build_edge_shape_mask(
    h: int,
    w: int,
    rng: random.Random,
    ew: int,
    eh: int,
) -> np.ndarray:
    edge = rng.choice([0, 1, 2, 3, 4, 5, 6, 7])

    if edge == 0:
        cx, cy = rng.randint(0, w), 0
    elif edge == 1:
        cx, cy = w, rng.randint(0, h)
    elif edge == 2:
        cx, cy = rng.randint(0, w), h
    elif edge == 3:
        cx, cy = 0, rng.randint(0, h)
    elif edge == 4:
        cx, cy = 0, 0
    elif edge == 5:
        cx, cy = w, 0
    elif edge == 6:
        cx, cy = w, h
    else:
        cx, cy = 0, h

    shape_type = rng.choice(["polygon", "ellipse"])
    shape_mask = np.zeros((h, w), dtype=np.uint8)

    if shape_type == "ellipse":
        axes = (
            rng.randint(max(1, ew // 2), max(2, ew)),
            rng.randint(max(1, eh // 2), max(2, eh)),
        )
        angle = rng.randint(0, 180)
        cv2.ellipse(shape_mask, (cx, cy), axes, angle, 0, 360, 255, -1)
    else:
        pts = []
        for _ in range(rng.randint(5, 10)):
            px = cx + rng.randint(-ew, ew)
            py = cy + rng.randint(-eh, eh)
            pts.append([px, py])

        cv2.fillPoly(shape_mask, np.array([pts], dtype=np.int32), 255)

    return shape_mask


def apply_edge_degredation(
    img: np.ndarray,
    mt: np.ndarray,
    mm: np.ndarray,
    rng: random.Random,
    cfg: Dict[str, Any],
    trace: List[Dict[str, Any]],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    h, w = img.shape[:2]

    prob = float(cfg.get("prob", 0.70))
    if rng.random() > prob:
        return img, mt, mm

    erasures_range = cfg.get("num_erasures", [2, 5])
    num_erasures = rng.randint(int(erasures_range[0]), int(erasures_range[1]))
    size_ratio = cfg.get("size_ratio", [0.05, 0.15])

    protect_math = bool(cfg.get("protect_math", True))
    math_guard_px = int(cfg.get("math_guard_px", 8))
    skip_if_remaining_area_lt = int(cfg.get("skip_if_remaining_area_lt", 64))

    math_protect = None
    if protect_math and np.any(mm > 0):
        k = max(1, math_guard_px)
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (2 * k + 1, 2 * k + 1),
        )
        math_protect = cv2.dilate(
            (mm > 0).astype(np.uint8) * 255,
            kernel,
            iterations=1,
        ) > 0

    applied = 0
    protected_hits = 0

    for _ in range(num_erasures):
        ew = max(4, int(w * rng.uniform(float(size_ratio[0]), float(size_ratio[1]))))
        eh = max(4, int(h * rng.uniform(float(size_ratio[0]), float(size_ratio[1]))))

        shape_mask = build_edge_shape_mask(h, w, rng, ew, eh)
        bool_mask = shape_mask > 0

        if math_protect is not None and np.any(bool_mask & math_protect):
            protected_hits += 1
            bool_mask = bool_mask & (~math_protect)

        if int(bool_mask.sum()) < skip_if_remaining_area_lt:
            continue

        if rng.random() < 0.75:
            color = (255, 255, 255) if img.ndim == 3 else 255
        else:
            gray_val = rng.randint(0, 60)
            color = (gray_val, gray_val, gray_val) if img.ndim == 3 else gray_val

        img[bool_mask] = color
        mt[bool_mask] = 0
        mm[bool_mask] = 0
        applied += 1

    trace.append(
        {
            "op": "edge_degredation",
            "requested_num_erasures": num_erasures,
            "applied_num_erasures": applied,
            "protect_math": protect_math,
            "protected_hits": protected_hits,
            "math_guard_px": math_guard_px if protect_math else 0,
        }
    )

    return img, mt, mm


def apply_elastic_distortion(
    img: np.ndarray,
    mt: np.ndarray,
    mm: np.ndarray,
    rng: random.Random,
    cfg: Dict[str, Any],
    trace: List[Dict[str, Any]],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    h, w = img.shape[:2]

    prob = float(cfg.get("prob", 0.35))
    if rng.random() > prob:
        return img, mt, mm

    alpha_range = cfg.get("alpha", [15.0, 25.0])
    sigma_range = cfg.get("sigma", [6.0, 10.0])

    alpha = rng.uniform(float(alpha_range[0]), float(alpha_range[1]))
    sigma = rng.uniform(float(sigma_range[0]), float(sigma_range[1]))

    np_rng = np_rng_from_rng(rng)

    dx = np_rng.uniform(-1.0, 1.0, (h, w)).astype(np.float32)
    dy = np_rng.uniform(-1.0, 1.0, (h, w)).astype(np.float32)

    dx = cv2.GaussianBlur(dx, (0, 0), sigma) * alpha
    dy = cv2.GaussianBlur(dy, (0, 0), sigma) * alpha

    x, y = np.meshgrid(
        np.arange(w, dtype=np.float32),
        np.arange(h, dtype=np.float32),
    )

    x_map = x + dx
    y_map = y + dy

    distorted_img = cv2.remap(
        img,
        x_map,
        y_map,
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    distorted_mt = cv2.remap(
        mt,
        x_map,
        y_map,
        cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    distorted_mm = cv2.remap(
        mm,
        x_map,
        y_map,
        cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )

    trace.append({"op": "elastic_distortion", "alpha": alpha, "sigma": sigma})

    return distorted_img, distorted_mt, distorted_mm



