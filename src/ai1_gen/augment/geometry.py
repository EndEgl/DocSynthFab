# src/ai1_gen/augment/geometry.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - opencv-python>=4.8,<5.0

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from .common import bbox_area, clip_bbox_xywh, warp


def apply_geometry_and_update_ann(
    img: np.ndarray,
    mt: np.ndarray,
    mm: np.ndarray,
    ann: Dict[str, Any],
    meta: Dict[str, Any],
    aug_cfg: Dict[str, Any],
    rng: random.Random,
    trace: List[Dict[str, Any]],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any], Optional[np.ndarray]]:
    h, w = img.shape[:2]
    cfg_geom = aug_cfg.get("geometry", {})

    rot0, rot1 = cfg_geom.get("rotation_deg", [-6.0, 6.0])

    if bool(meta.get("has_equation", False)):
        rot0, rot1 = max(-4.0, float(rot0)), min(4.0, float(rot1))

    if bool(meta.get("has_table", False)):
        rot0, rot1 = max(-3.0, float(rot0)), min(3.0, float(rot1))

    rot = rng.uniform(float(rot0), float(rot1))

    cx, cy = w / 2.0, h / 2.0
    m2 = cv2.getRotationMatrix2D((cx, cy), rot, 1.0)

    matrix = np.eye(3, dtype=np.float32)
    matrix[:2, :] = m2

    pj0, pj1 = cfg_geom.get("perspective_jitter_ratio", [0.0, 0.03])

    if bool(meta.get("has_table", False)):
        pj1 = min(float(pj1), 0.015)
    elif bool(meta.get("has_equation", False)):
        pj1 = min(float(pj1), 0.02)

    jitter = rng.uniform(float(pj0), float(pj1)) * float(min(w, h))

    if float(jitter) > 0 and bool(meta.get("perspective", False)):
        src = np.float32(
            [
                [0, 0],
                [w - 1, 0],
                [w - 1, h - 1],
                [0, h - 1],
            ]
        )
        dst = src + np.float32(
            [
                [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
            ]
        )

        perspective = cv2.getPerspectiveTransform(src, dst)
        matrix = perspective @ matrix

    geom_m = matrix.astype(np.float32)

    img = warp(img, geom_m, (w, h), is_mask=False)
    mt = warp(mt, geom_m, (w, h), is_mask=True)
    mm = warp(mm, geom_m, (w, h), is_mask=True)

    trace.append(
        {
            "op": "geometry",
            "rotation_deg": rot,
            "perspective": bool(meta.get("perspective", False)),
        }
    )

    min_area_val = aug_cfg.get("min_area_px", 25)
    min_area = int(min_area_val) if isinstance(min_area_val, (int, float)) else 25

    def tx_point(px: float, py: float) -> Tuple[float, float]:
        v = np.array([px, py, 1.0], dtype=np.float32)
        transformed = geom_m @ v

        if abs(float(transformed[2])) < 1e-6:
            return px, py

        return (
            float(transformed[0] / transformed[2]),
            float(transformed[1] / transformed[2]),
        )

    kept_lines = []

    for line in ann.get("lines", []) or []:
        b = line.get("bbox", [0, 0, 0, 0])
        x, y, bw, bh = map(float, b)

        pts = [
            (x, y),
            (x + bw, y),
            (x + bw, y + bh),
            (x, y + bh),
        ]

        transformed_pts = [tx_point(px, py) for px, py in pts]
        xs = [p[0] for p in transformed_pts]
        ys = [p[1] for p in transformed_pts]

        nx0, ny0 = min(xs), min(ys)
        nx1, ny1 = max(xs), max(ys)

        new_bbox = [
            int(nx0),
            int(ny0),
            int(nx1 - nx0),
            int(ny1 - ny0),
        ]

        new_bbox = clip_bbox_xywh(new_bbox, w, h)

        if bbox_area(new_bbox) < min_area:
            continue

        line["bbox"] = new_bbox
        kept_lines.append(line)

    for idx, line in enumerate(kept_lines):
        line["global_line_order"] = idx

    ann["lines"] = kept_lines

    block_to_line_boxes: Dict[int, List[List[int]]] = {}

    for line in kept_lines:
        block_id = int(line.get("block_id", -1))
        block_to_line_boxes.setdefault(block_id, []).append(line["bbox"])

    kept_blocks = []

    for block in ann.get("blocks", []) or []:
        block_id = int(block.get("block_id", -1))
        boxes = block_to_line_boxes.get(block_id, [])

        if not boxes:
            continue

        xs = [b[0] for b in boxes]
        ys = [b[1] for b in boxes]
        x2 = [b[0] + b[2] for b in boxes]
        y2 = [b[1] + b[3] for b in boxes]

        new_bbox = [
            min(xs),
            min(ys),
            max(x2) - min(xs),
            max(y2) - min(ys),
        ]

        block["bbox"] = clip_bbox_xywh(new_bbox, w, h)
        kept_blocks.append(block)

    ann["blocks"] = kept_blocks

    return img, mt, mm, ann, geom_m