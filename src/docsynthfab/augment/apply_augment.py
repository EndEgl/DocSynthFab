# src/docsynthfab/augment/apply_augment.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

import copy
import random
from typing import Any, Dict, Optional

import numpy as np

from .capture import apply_capture_sim
from .common import bbox_area as _bbox_area
from .common import clip_bbox_xywh as _clip_bbox_xywh
from .degradation import apply_edge_degredation, apply_elastic_distortion
from .geometry import apply_geometry_and_update_ann
from .noise import apply_blur_noise
from .photometric import apply_photometric
from .policy import build_aug_plan
from .quality import quick_quality_gate, sync_meta_from_annotation_and_masks
from .result import AugResult


def apply_augment(
    image_u8: np.ndarray,
    mask_text_u8: np.ndarray,
    mask_math_u8: np.ndarray,
    ann: Dict[str, Any],
    meta: Dict[str, Any],
    aug_cfg: Dict[str, Any],
    rng: random.Random,
) -> AugResult:
    trace = []

    img = image_u8.copy()
    mt = mask_text_u8.copy()
    mm = mask_math_u8.copy()
    ann_work = copy.deepcopy(ann)

    before_mt = mt.copy()
    before_mm = mm.copy()

    chosen = build_aug_plan(meta, aug_cfg, rng)

    scale_profile = str(meta.get("scale_profile", "dpi300"))

    if scale_profile == "lowres_capture" and not chosen["capture"]:
        chosen["capture"] = True
        trace.append(
            {
                "op": "policy_enforce",
                "reason": "lowres_required_missing",
                "code": "aug/lowres-required-missing",
            }
        )

    cfg_photo = aug_cfg.get("photometric", {})
    cfg_blur = aug_cfg.get("blur_noise", {})
    cfg_capture = aug_cfg.get("capture_sim", {})
    cfg_edge = aug_cfg.get("edge_degredation", {})
    cfg_elastic = aug_cfg.get("elastic_distortion", {})

    noise_level = str(meta.get("noise_level", "clean"))

    if chosen["photometric"]:
        img = apply_photometric(img, rng, cfg_photo, trace)

    if chosen["blur_noise"]:
        img = apply_blur_noise(img, rng, cfg_blur, trace)

    if chosen["capture"]:
        capture_noise_level = "heavy" if scale_profile == "lowres_capture" else noise_level
        img = apply_capture_sim(img, rng, cfg_capture, capture_noise_level, trace)

    if chosen["edge"]:
        img, mt, mm = apply_edge_degredation(img, mt, mm, rng, cfg_edge, trace)

    if chosen["elastic"]:
        img, mt, mm = apply_elastic_distortion(img, mt, mm, rng, cfg_elastic, trace)

    geom_m: Optional[np.ndarray] = None

    if chosen["geometry"]:
        img, mt, mm, ann_work, geom_m = apply_geometry_and_update_ann(
            img,
            mt,
            mm,
            ann_work,
            meta,
            aug_cfg,
            rng,
            trace,
        )

    mt = np.where(mt > 127, 255, 0).astype(np.uint8)
    mm = np.where(mm > 127, 255, 0).astype(np.uint8)

    ok, gate_metrics = quick_quality_gate(before_mt, before_mm, mt, mm, meta)

    trace.append(
        {
            "op": "quick_quality_gate",
            **gate_metrics,
            "accepted": bool(ok),
        }
    )

    if not ok:
        trace.append({"op": "fallback_to_light_plan"})

        img = image_u8.copy()
        mt = mask_text_u8.copy()
        mm = mask_math_u8.copy()
        ann_work = copy.deepcopy(ann)
        geom_m = None

        if chosen["photometric"]:
            img = apply_photometric(img, rng, cfg_photo, trace)

        if chosen["capture"]:
            img = apply_capture_sim(img, rng, cfg_capture, noise_level, trace)

        mt = np.where(mt > 127, 255, 0).astype(np.uint8)
        mm = np.where(mm > 127, 255, 0).astype(np.uint8)

    sync_meta_from_annotation_and_masks(ann_work, mt, mm)

    return AugResult(
        image_aug_u8=img,
        mask_text_aug_u8=mt,
        mask_math_aug_u8=mm,
        ann_aug=ann_work,
        aug_trace=trace,
        geom_M=geom_m,
    )



