# src/ai1_gen/augment/apply_augment.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - opencv-python>=4.8,<5.0
# - Pillow>=10,<12

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random
import math
import io

import numpy as np
import cv2
from PIL import Image


@dataclass
class AugResult:
    image_aug_u8: np.ndarray
    mask_text_aug_u8: np.ndarray
    mask_math_aug_u8: np.ndarray
    ann_aug: Dict[str, Any]
    aug_trace: List[Dict[str, Any]]
    geom_M: Optional[np.ndarray]


def _clip_bbox_xywh(b: List[int], w: int, h: int) -> List[int]:
    x, y, bw, bh = (int(b[0]), int(b[1]), int(b[2]), int(b[3]))
    x = max(0, min(x, w - 1))
    y = max(0, min(y, h - 1))
    bw = max(0, min(bw, w - x))
    bh = max(0, min(bh, h - y))
    return [x, y, bw, bh]


def _bbox_area(b: List[int]) -> int:
    return int(b[2]) * int(b[3])


def _warp(image: np.ndarray, M: np.ndarray, out_wh: Tuple[int, int], is_mask: bool) -> np.ndarray:
    ow, oh = out_wh
    interp = cv2.INTER_NEAREST if is_mask else cv2.INTER_LINEAR
    border = (255, 255, 255) if image.ndim == 3 else 0
    warped = cv2.warpPerspective(image, M, (ow, oh), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=border)
    return warped


def _apply_photometric(img: np.ndarray, rng: random.Random, cfg: Dict[str, Any], trace: List[Dict[str, Any]]) -> np.ndarray:
    # GÜVENLİ ERİŞİM: KeyError önlemek için .get() ve varsayılan değerler
    # gamma
    g0, g1 = cfg.get("gamma", [0.75, 1.25])
    gamma = rng.uniform(float(g0), float(g1))
    inv = 1.0 / max(1e-6, gamma)
    lut = np.array([(i / 255.0) ** inv * 255.0 for i in range(256)], dtype=np.uint8)
    out = cv2.LUT(img, lut)

    # brightness/contrast
    b0, b1 = cfg.get("brightness", [-20, 20])
    c0, c1 = cfg.get("contrast", [0.85, 1.20])
    beta = rng.uniform(float(b0), float(b1))
    alpha = rng.uniform(float(c0), float(c1))
    out = cv2.convertScaleAbs(out, alpha=alpha, beta=beta)

    trace.append({"op": "photometric", "gamma": gamma, "alpha": alpha, "beta": beta})
    return out


def _apply_blur_noise(img: np.ndarray, rng: random.Random, cfg: Dict[str, Any], trace: List[Dict[str, Any]]) -> np.ndarray:
    out = img

    # GÜVENLİ ERİŞİM
    # gaussian blur
    k_choices = cfg.get("gaussian_kernel_choices", [3, 5, 7])
    k = int(rng.choice(k_choices))
    if k % 2 == 0:
        k += 1
    out = cv2.GaussianBlur(out, (k, k), 0)

    # speckle noise
    s0, s1 = cfg.get("speckle", [0.02, 0.10])
    sp = rng.uniform(float(s0), float(s1))
    noise = rng.normalvariate(0.0, sp)
    n = np.random.randn(*out.shape).astype(np.float32) * float(sp) * 255.0
    out_f = out.astype(np.float32) + n
    out = np.clip(out_f, 0, 255).astype(np.uint8)

    trace.append({"op": "blur_noise", "gauss_k": k, "speckle": sp})
    return out


def _apply_capture_sim(img: np.ndarray, rng: random.Random, cfg: Dict[str, Any], noise_level: str, trace: List[Dict[str, Any]]) -> np.ndarray:
    h, w = img.shape[:2]
    
    # GÜVENLİ ERİŞİM
    f0, f1 = cfg.get("downscale_factor", [0.50, 0.85])
    factor = rng.uniform(float(f0), float(f1))
    dw = max(8, int(w * factor))
    dh = max(8, int(h * factor))
    small = cv2.resize(img, (dw, dh), interpolation=cv2.INTER_AREA)
    up = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)

    if noise_level in ("heavy",):
        q0, q1 = cfg.get("jpeg_quality_heavy", [25, 70])
    else:
        q0, q1 = cfg.get("jpeg_quality_clean_medium", [40, 90])
    q = int(rng.uniform(float(q0), float(q1)))

    # JPEG roundtrip via PIL (boyut invariants)
    pil = Image.fromarray(up)
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=q, optimize=False)
    buf.seek(0)
    pil2 = Image.open(buf).convert("RGB")
    out = np.array(pil2, dtype=np.uint8)

    trace.append({"op": "capture_sim", "downscale_factor": factor, "jpeg_quality": q})
    return out


def _sample_policy(rng: random.Random, pol: Dict[str, float]) -> Dict[str, bool]:
    def _b(p: float) -> bool:
        return rng.random() < float(p)

    return {
        "photometric": _b(pol.get("p_photometric", 0.4)),
        "blur_noise": _b(pol.get("p_blur_noise", 0.25)),
        "capture": _b(pol.get("p_capture", 0.15)),
        "geometry": _b(pol.get("p_geometry", 0.10)),
    }


def apply_augment(
    image_u8: np.ndarray,
    mask_text_u8: np.ndarray,
    mask_math_u8: np.ndarray,
    ann: Dict[str, Any],
    meta: Dict[str, Any],
    aug_cfg: Dict[str, Any],
    rng: random.Random,
) -> AugResult:
    """
    Kontrat v1.3.2 deterministik sıra:
      1 Photometric (image)
      2 Blur/Noise (image)
      3 Capture sim (image, size invariant)
      4 Geometry (image+masks+ann aynı matris)
      5 Final mask binarize
    """
    trace: List[Dict[str, Any]] = []
    img = image_u8.copy() # Orijinal veriyi bozmamak için kopyalama iyi bir pratiktir
    mt = mask_text_u8.copy()
    mm = mask_math_u8.copy()

    H, W = img.shape[:2]

    # policy by noise_level
    selpol = aug_cfg.get("selection_policy", {})
    noise_level = str(meta.get("noise_level", "clean"))
    pol = selpol.get(noise_level, selpol.get("clean", {}))
    chosen = _sample_policy(rng, pol)

    # lowres_capture zorunluluğu
    scale_profile = str(meta.get("scale_profile", "dpi300"))
    if scale_profile == "lowres_capture" and not chosen["capture"]:
        # zorunlu
        chosen["capture"] = True
        trace.append({"op": "policy_enforce", "reason": "lowres_required_missing", "code": "aug/lowres-required-missing"})

    # GÜVENLİ ERİŞİM: Alt konfigürasyon sözlüklerini (varsa) al, yoksa boş sözlük gönder
    cfg_photo = aug_cfg.get("photometric", {})
    cfg_blur = aug_cfg.get("blur_noise", {})
    cfg_capture = aug_cfg.get("capture_sim", {})
    cfg_geom = aug_cfg.get("geometry", {})

    # 1 Photometric
    if chosen["photometric"]:
        img = _apply_photometric(img, rng, cfg_photo, trace)

    # 2 Blur/Noise
    if chosen["blur_noise"]:
        img = _apply_blur_noise(img, rng, cfg_blur, trace)

    # 3 Capture sim (size invariant)
    if chosen["capture"]:
        img = _apply_capture_sim(img, rng, cfg_capture, noise_level, trace)

    # 4 Geometry
    geom_M: Optional[np.ndarray] = None
    if chosen["geometry"]:
        rot0, rot1 = cfg_geom.get("rotation_deg", [-6.0, 6.0])
        rot = rng.uniform(float(rot0), float(rot1))

        # rotation matrix around center (as homography)
        cx, cy = W / 2.0, H / 2.0
        M2 = cv2.getRotationMatrix2D((cx, cy), rot, 1.0)  # 2x3
        M = np.eye(3, dtype=np.float32)
        M[:2, :] = M2

        # perspective jitter
        pj0, pj1 = cfg_geom.get("perspective_jitter_ratio", [0.0, 0.03])
        jitter = rng.uniform(float(pj0), float(pj1)) * float(min(W, H))
        if float(jitter) > 0 and bool(meta.get("perspective", False)):
            src = np.float32([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]])
            dst = src + np.float32([
                [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
            ])
            P = cv2.getPerspectiveTransform(src, dst)
            M = P @ M

        # crop jitter via translating bounds (basit yaklaşım: uygula, sonra aynı boyuta warp)
        geom_M = M.astype(np.float32)

        img = _warp(img, geom_M, (W, H), is_mask=False)
        mt = _warp(mt, geom_M, (W, H), is_mask=True)
        mm = _warp(mm, geom_M, (W, H), is_mask=True)

        trace.append({"op": "geometry", "rotation_deg": rot, "perspective": bool(meta.get("perspective", False))})

        # ann bbox update
        min_area_val = aug_cfg.get("min_area_px", 25)
        min_area = int(min_area_val) if isinstance(min_area_val, (int, float)) else 25
        
        lines = ann.get("lines", [])
        blocks = ann.get("blocks", [])

        def tx_point(px: float, py: float) -> Tuple[float, float]:
            v = np.array([px, py, 1.0], dtype=np.float32)
            wv = geom_M @ v
            if abs(float(wv[2])) < 1e-6:
                return (px, py)
            return (float(wv[0] / wv[2]), float(wv[1] / wv[2]))

        # update line bbox, drop invalid
        kept_lines = []
        for ln in lines:
            b = ln.get("bbox", [0, 0, 0, 0])
            x, y, bw, bh = map(float, b)
            pts = [(x, y), (x + bw, y), (x + bw, y + bh), (x, y + bh)]
            tpts = [tx_point(px, py) for px, py in pts]
            xs = [p[0] for p in tpts]
            ys = [p[1] for p in tpts]
            nx0, ny0 = min(xs), min(ys)
            nx1, ny1 = max(xs), max(ys)
            nb = [int(nx0), int(ny0), int(nx1 - nx0), int(ny1 - ny0)]
            nb = _clip_bbox_xywh(nb, W, H)
            if _bbox_area(nb) < min_area:
                continue
            ln["bbox"] = nb
            kept_lines.append(ln)

        # reindex global order
        for k, ln in enumerate(kept_lines):
            ln["global_line_order"] = k

        ann["lines"] = kept_lines

        # recompute block bbox from lines
        blk_map: Dict[int, List[List[int]]] = {}
        for ln in kept_lines:
            bid = int(ln.get("block_id", -1))
            blk_map.setdefault(bid, []).append(ln["bbox"])

        kept_blocks = []
        for b in blocks:
            bid = int(b.get("block_id", -1))
            boxes = blk_map.get(bid, [])
            if not boxes:
                continue
            xs = [bb[0] for bb in boxes]
            ys = [bb[1] for bb in boxes]
            x2 = [bb[0] + bb[2] for bb in boxes]
            y2 = [bb[1] + bb[3] for bb in boxes]
            nb = [min(xs), min(ys), max(x2) - min(xs), max(y2) - min(ys)]
            nb = _clip_bbox_xywh(nb, W, H)
            b["bbox"] = nb
            kept_blocks.append(b)
        ann["blocks"] = kept_blocks

    # 5 final mask binarize
    mt = np.where(mt > 0, 255, 0).astype(np.uint8)
    mm = np.where(mm > 0, 255, 0).astype(np.uint8)

    return AugResult(
        image_aug_u8=img,
        mask_text_aug_u8=mt,
        mask_math_aug_u8=mm,
        ann_aug=ann,
        aug_trace=trace,
        geom_M=geom_M,
    )