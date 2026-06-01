# src/ai1_gen/augment/noise.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - opencv-python>=4.8,<5.0

from __future__ import annotations

import random
from typing import Any, Dict, List

import cv2
import numpy as np

from .common import np_rng_from_rng


def apply_blur_noise(
    img: np.ndarray,
    rng: random.Random,
    cfg: Dict[str, Any],
    trace: List[Dict[str, Any]],
) -> np.ndarray:
    out = img.copy()
    h, w = out.shape[:2]
    np_rng = np_rng_from_rng(rng)

    if rng.random() < 0.30:
        blur_type = rng.choice(["gaussian", "motion"])

        if blur_type == "gaussian":
            k_choices = cfg.get("gaussian_kernel_choices", [3, 5])
            k = int(rng.choice(k_choices))
            k = k if k % 2 == 1 else k + 1
            out = cv2.GaussianBlur(out, (k, k), 0)
        else:
            k = int(rng.choice([3, 5, 7, 9]))
            kernel_m = np.zeros((k, k), dtype=np.float32)
            direction = rng.choice(["h", "v", "d1", "d2"])

            if direction == "h":
                kernel_m[k // 2, :] = 1.0
            elif direction == "v":
                kernel_m[:, k // 2] = 1.0
            elif direction == "d1":
                np.fill_diagonal(kernel_m, 1.0)
            else:
                np.fill_diagonal(np.fliplr(kernel_m), 1.0)

            kernel_m /= np.sum(kernel_m)
            out = cv2.filter2D(out, -1, kernel_m)

        trace.append({"op": "blur", "type": blur_type, "k": k})

    if rng.random() < 0.35:
        sp_range = cfg.get("speckle", [0.006, 0.028])
        sp = rng.uniform(float(sp_range[0]), float(sp_range[1]))

        n = np_rng.normal(
            loc=0.0,
            scale=float(sp) * 255.0,
            size=out.shape,
        ).astype(np.float32)

        out = np.clip(out.astype(np.float32) + n, 0, 255).astype(np.uint8)
        trace.append({"op": "speckle_noise", "amount": sp})

    if rng.random() < 0.22:
        num_scratches = rng.randint(1, 7)
        applied = []

        for _ in range(num_scratches):
            x0 = rng.randint(0, max(0, w - 1))
            y0 = rng.randint(0, max(0, h - 1))

            length = rng.randint(max(20, h // 12), max(30, h // 2))
            angle = rng.uniform(-35.0, 35.0)
            thickness = rng.randint(1, 3)

            dx = int(np.cos(np.deg2rad(angle)) * length * 0.25)
            dy = int(length)

            x1 = int(np.clip(x0 + dx, 0, w - 1))
            y1 = int(np.clip(y0 + dy, 0, h - 1))

            overlay = out.copy()
            val = rng.randint(205, 250)
            color = (val, val, val) if out.ndim == 3 else val

            cv2.line(
                overlay,
                (x0, y0),
                (x1, y1),
                color,
                thickness=thickness,
                lineType=cv2.LINE_AA,
            )

            alpha = rng.uniform(0.08, 0.28)
            out = cv2.addWeighted(overlay, alpha, out, 1.0 - alpha, 0.0)

            applied.append(
                {
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "thickness": thickness,
                    "alpha": alpha,
                }
            )

        trace.append(
            {
                "op": "irregular_scratches",
                "count": num_scratches,
                "items": applied[:5],
            }
        )

    if rng.random() < 0.26:
        num_blobs = rng.randint(2, 10)
        blob_mask = np.zeros((h, w), dtype=np.uint8)

        for _ in range(num_blobs):
            cx = rng.randint(0, max(0, w - 1))
            cy = rng.randint(0, max(0, h - 1))
            rx = rng.randint(max(6, w // 120), max(10, w // 30))
            ry = rng.randint(max(6, h // 120), max(10, h // 30))
            angle = rng.randint(0, 180)

            cv2.ellipse(blob_mask, (cx, cy), (rx, ry), angle, 0, 360, 255, -1)

        k = rng.choice([9, 13, 17, 21])
        blob_mask = cv2.GaussianBlur(blob_mask, (k, k), 0)

        if out.ndim == 3:
            blob_mask_f = (blob_mask.astype(np.float32) / 255.0)[..., None]
        else:
            blob_mask_f = blob_mask.astype(np.float32) / 255.0

        darken = rng.uniform(0.80, 0.96)
        out = np.clip(
            out.astype(np.float32) * (1.0 - blob_mask_f * (1.0 - darken)),
            0,
            255,
        ).astype(np.uint8)

        trace.append({"op": "dirty_blobs", "count": num_blobs, "darken": darken})

    if rng.random() < 0.24:
        small_w = max(8, w // rng.randint(18, 36))
        small_h = max(8, h // rng.randint(18, 36))

        illum_small = np_rng.uniform(0.0, 1.0, (small_h, small_w)).astype(np.float32)
        illum_small = cv2.GaussianBlur(
            illum_small,
            (0, 0),
            sigmaX=rng.uniform(2.0, 5.0),
        )

        illum = cv2.resize(illum_small, (w, h), interpolation=cv2.INTER_CUBIC)
        illum -= illum.min()

        denom = float(illum.max())
        if denom > 1e-6:
            illum /= denom
            drop = rng.uniform(0.08, 0.30)
            gain = 1.0 - illum * drop

            if out.ndim == 3:
                gain = gain[..., None]

            out = np.clip(out.astype(np.float32) * gain, 0, 255).astype(np.uint8)
            trace.append({"op": "lowfreq_illumination", "drop": drop})

    if rng.random() < 0.20:
        band_overlay = out.astype(np.float32).copy()
        num_bands = rng.randint(1, 6)

        for _ in range(num_bands):
            horizontal = rng.random() < 0.65
            alpha = rng.uniform(0.03, 0.12)

            if horizontal:
                y = rng.randint(0, max(0, h - 1))
                bh = rng.randint(2, max(3, h // 40))
                y2 = min(h, y + bh)
                factor = rng.uniform(0.82, 1.05)
                band_overlay[y:y2, ...] *= factor
            else:
                x = rng.randint(0, max(0, w - 1))
                bw = rng.randint(2, max(3, w // 40))
                x2 = min(w, x + bw)
                factor = rng.uniform(0.82, 1.05)
                band_overlay[:, x:x2, ...] *= factor

            out = np.clip(
                (1.0 - alpha) * out.astype(np.float32) + alpha * band_overlay,
                0,
                255,
            ).astype(np.uint8)

        trace.append({"op": "irregular_banding", "count": num_bands})

    if rng.random() < 0.12:
        amount = rng.uniform(0.0005, 0.0045)
        num_pixels = h * w

        num_salt = int(np.ceil(amount * num_pixels * rng.uniform(0.25, 0.55)))
        num_pepper = int(np.ceil(amount * num_pixels * rng.uniform(0.45, 0.75)))

        r_salt = np_rng.integers(0, h, num_salt)
        c_salt = np_rng.integers(0, w, num_salt)
        r_pep = np_rng.integers(0, h, num_pepper)
        c_pep = np_rng.integers(0, w, num_pepper)

        if out.ndim == 3:
            out[r_salt, c_salt] = (255, 255, 255)
            dark_val = rng.randint(0, 45)
            out[r_pep, c_pep] = (dark_val, dark_val, dark_val)
        else:
            out[r_salt, c_salt] = 255
            out[r_pep, c_pep] = rng.randint(0, 45)

        trace.append({"op": "salt_pepper", "amount": amount})

    return out