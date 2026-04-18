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
    warped = cv2.warpPerspective(
        image,
        M,
        (ow, oh),
        flags=interp,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border,
    )
    return warped


def _np_rng_from_rng(rng: random.Random) -> np.random.Generator:
    return np.random.default_rng(rng.randint(0, 2**32 - 1))


def _apply_photometric(
    img: np.ndarray,
    rng: random.Random,
    cfg: Dict[str, Any],
    trace: List[Dict[str, Any]],
) -> np.ndarray:
    g0, g1 = cfg.get("gamma", [0.75, 1.25])
    gamma = rng.uniform(float(g0), float(g1))
    inv = 1.0 / max(1e-6, gamma)
    lut = np.array([(i / 255.0) ** inv * 255.0 for i in range(256)], dtype=np.uint8)
    out = cv2.LUT(img, lut)

    b0, b1 = cfg.get("brightness", [-20, 20])
    c0, c1 = cfg.get("contrast", [0.85, 1.20])
    beta = rng.uniform(float(b0), float(b1))
    alpha = rng.uniform(float(c0), float(c1))
    out = cv2.convertScaleAbs(out, alpha=alpha, beta=beta)

    trace.append({"op": "photometric", "gamma": gamma, "alpha": alpha, "beta": beta})
    return out


def _apply_blur_noise(
    img: np.ndarray,
    rng: random.Random,
    cfg: Dict[str, Any],
    trace: List[Dict[str, Any]],
) -> np.ndarray:
    out = img.copy()
    h, w = out.shape[:2]
    np_rng = _np_rng_from_rng(rng)

    # 1. Blur (Gaussian veya Hareket Bulanıklığı - Motion Blur)
    if rng.random() < 0.35:
        blur_type = rng.choice(["gaussian", "motion"])
        if blur_type == "gaussian":
            k_choices = cfg.get("gaussian_kernel_choices", [3, 5])
            k = int(rng.choice(k_choices))
            k = k if k % 2 == 1 else k + 1
            out = cv2.GaussianBlur(out, (k, k), 0)
        else:
            # Kamera titremesi / kayma simülasyonu (Motion blur)
            k = int(rng.choice([3, 5, 7]))
            kernel_m = np.zeros((k, k), dtype=np.float32)
            direction = rng.choice(["h", "v", "d1", "d2"]) # yatay, dikey veya çapraz
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

    # 2. Speckle (Sensör Gürültüsü / Gren)
    if rng.random() < 0.40:
        sp_range = cfg.get("speckle", [0.01, 0.05])
        sp = rng.uniform(float(sp_range[0]), float(sp_range[1]))
        n = np_rng.normal(loc=0.0, scale=float(sp) * 255.0, size=out.shape).astype(np.float32)
        out_f = out.astype(np.float32) + n
        out = np.clip(out_f, 0, 255).astype(np.uint8)
        trace.append({"op": "speckle_noise", "amount": sp})

    # 3. Salt & Pepper (Toner tozu / Siyah-Beyaz Noktacıklar)
    if rng.random() < 0.25:
        amount = rng.uniform(0.001, 0.015) # Piksellerin %0.1 ile %1.5'i
        s_vs_p = 0.5 # Yarısı beyaz, yarısı siyah
        num_pixels = h * w
        
        # Salt (Beyaz noktalar)
        num_salt = int(np.ceil(amount * num_pixels * s_vs_p))
        r_salt = np_rng.integers(0, h, num_salt)
        c_salt = np_rng.integers(0, w, num_salt)
        if out.ndim == 3:
            out[r_salt, c_salt] = (255, 255, 255)
        else:
            out[r_salt, c_salt] = 255

        # Pepper (Siyah noktalar / Toner lekeleri)
        num_pepper = int(np.ceil(amount * num_pixels * (1.0 - s_vs_p)))
        r_pep = np_rng.integers(0, h, num_pepper)
        c_pep = np_rng.integers(0, w, num_pepper)
        if out.ndim == 3:
            # Gerçekçi olması için tam siyah değil, koyu gri de olabilir
            dark_val = rng.randint(0, 50)
            out[r_pep, c_pep] = (dark_val, dark_val, dark_val) 
        else:
            out[r_pep, c_pep] = rng.randint(0, 50)
            
        trace.append({"op": "salt_pepper", "amount": amount})

    # 4. Tarayıcı Çizgileri (Scanner Streaks / Kirli Cam Sensörü)
    if rng.random() < 0.15:
        num_lines = rng.randint(1, 4)
        for _ in range(num_lines):
            x_pos = rng.randint(0, max(1, w - 5))
            line_w = rng.randint(1, 3)
            alpha = rng.uniform(0.70, 0.95) # Çizginin koyuluğu
            streak = out[:, x_pos:x_pos+line_w].astype(np.float32) * alpha
            out[:, x_pos:x_pos+line_w] = np.clip(streak, 0, 255).astype(np.uint8)
        trace.append({"op": "scanner_streaks", "count": num_lines})

    # 5. Dengesiz Işıklandırma (Gradient Shadow / Kötü Kamera Işığı)
    if rng.random() < 0.20:
        xx, yy = np.meshgrid(np.linspace(0, 1, w, dtype=np.float32), np.linspace(0, 1, h, dtype=np.float32))
        direction = rng.choice([xx, yy, xx+yy, xx-yy])
        direction = direction - np.min(direction)
        direction = direction / np.max(direction) # 0 ile 1 arasına normalize et
        
        # Parlaklık düşüş oranı (örn. 0.6 = bölge bölge %40'a varan kararma)
        drop = rng.uniform(0.5, 0.85)
        gradient = 1.0 - (direction * (1.0 - drop))
        
        if out.ndim == 3:
            gradient = np.expand_dims(gradient, axis=-1)
            
        out = np.clip(out.astype(np.float32) * gradient, 0, 255).astype(np.uint8)
        trace.append({"op": "uneven_illumination", "drop": drop})

    return out


def _apply_capture_sim(
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

        trace.append({"op": "capture_sim", "downscale_factor": factor, "jpeg_quality": q})
        return out

    return img


def _sample_policy(rng: random.Random, pol: Dict[str, float]) -> Dict[str, bool]:
    def _b(p: float) -> bool:
        return rng.random() < float(p)

    return {
        "photometric": _b(pol.get("p_photometric", 0.4)),
        "blur_noise": _b(pol.get("p_blur_noise", 0.25)),
        "capture": _b(pol.get("p_capture", 0.15)),
        "geometry": _b(pol.get("p_geometry", 0.10)),
    }


def _build_edge_shape_mask(
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
        axes = (rng.randint(max(1, ew // 2), max(2, ew)), rng.randint(max(1, eh // 2), max(2, eh)))
        angle = rng.randint(0, 180)
        cv2.ellipse(shape_mask, (cx, cy), axes, angle, 0, 360, 255, -1)
    else:
        num_points = rng.randint(5, 10)
        pts = []
        for _ in range(num_points):
            px = cx + rng.randint(-ew, ew)
            py = cy + rng.randint(-eh, eh)
            pts.append([px, py])
        pts_array = np.array([pts], dtype=np.int32)
        cv2.fillPoly(shape_mask, pts_array, 255)

    return shape_mask


def _apply_edge_degredation(
    img: np.ndarray,
    mt: np.ndarray,
    mm: np.ndarray,
    rng: random.Random,
    cfg: Dict[str, Any],
    trace: List[Dict[str, Any]],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Kenarlardan ve köşelerden rastgele organik şekiller (yırtık, yuvarlak kopuk,
    siyah tarayıcı gölgesi vb.) ekler. Nadir olan math mask'in tamamen kaybolmaması
    için varsayılan olarak math bölgeleri korunur.
    """
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
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
        math_protect = cv2.dilate((mm > 0).astype(np.uint8) * 255, kernel, iterations=1) > 0

    applied = 0
    protected_hits = 0

    for _ in range(num_erasures):
        ew = max(4, int(w * rng.uniform(float(size_ratio[0]), float(size_ratio[1]))))
        eh = max(4, int(h * rng.uniform(float(size_ratio[0]), float(size_ratio[1]))))

        shape_mask = _build_edge_shape_mask(h, w, rng, ew, eh)
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

        if img.ndim == 3:
            img[bool_mask] = color
        else:
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


def _apply_elastic_distortion(
    img: np.ndarray,
    mt: np.ndarray,
    mm: np.ndarray,
    rng: random.Random,
    cfg: Dict[str, Any],
    trace: List[Dict[str, Any]],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Kâğıdın buruşukluğunu simüle etmek için elastik deformasyon uygular.
    """
    h, w = img.shape[:2]

    prob = float(cfg.get("prob", 0.35))
    if rng.random() > prob:
        return img, mt, mm

    alpha_range = cfg.get("alpha", [15.0, 25.0])
    sigma_range = cfg.get("sigma", [6.0, 10.0])

    alpha = rng.uniform(float(alpha_range[0]), float(alpha_range[1]))
    sigma = rng.uniform(float(sigma_range[0]), float(sigma_range[1]))

    np_rng = _np_rng_from_rng(rng)
    dx = np_rng.uniform(-1.0, 1.0, (h, w)).astype(np.float32)
    dy = np_rng.uniform(-1.0, 1.0, (h, w)).astype(np.float32)

    dx = cv2.GaussianBlur(dx, (0, 0), sigma) * alpha
    dy = cv2.GaussianBlur(dy, (0, 0), sigma) * alpha

    x, y = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
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


def _sync_meta_from_annotation_and_masks(
    ann: Dict[str, Any],
    mt: np.ndarray,
    mm: np.ndarray,
) -> None:
    meta = ann.setdefault("meta", {})
    lines = ann.get("lines", []) or []
    blocks = ann.get("blocks", []) or []

    has_math_line = any(str(ln.get("line_type", "")) == "math" for ln in lines)
    has_table_block = any(str(b.get("block_type", "")) == "table" for b in blocks)
    has_figure_block = any(str(b.get("block_type", "")) == "figure" for b in blocks)

    meta["has_equation"] = bool(has_math_line and np.any(mm > 0))
    meta["has_table"] = bool(has_table_block)
    meta["has_figure"] = bool(has_figure_block)
    meta["mask_text_nonzero"] = int(np.count_nonzero(mt))
    meta["mask_math_nonzero"] = int(np.count_nonzero(mm))


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
      3.5 Edge Degredation
      3.7 Elastic Distortion
      4 Geometry (image+masks+ann aynı matris)
      5 Final mask binarize
    """
    trace: List[Dict[str, Any]] = []
    img = image_u8.copy()
    mt = mask_text_u8.copy()
    mm = mask_math_u8.copy()

    H, W = img.shape[:2]

    selpol = aug_cfg.get("selection_policy", {})
    noise_level = str(meta.get("noise_level", "clean"))
    pol = selpol.get(noise_level, selpol.get("clean", {}))
    chosen = _sample_policy(rng, pol)

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
    cfg_geom = aug_cfg.get("geometry", {})

    if chosen["photometric"]:
        img = _apply_photometric(img, rng, cfg_photo, trace)

    if chosen["blur_noise"]:
        img = _apply_blur_noise(img, rng, cfg_blur, trace)

    if chosen["capture"]:
        img = _apply_capture_sim(img, rng, cfg_capture, noise_level, trace)

    cfg_edge = aug_cfg.get("edge_degredation", {})
    img, mt, mm = _apply_edge_degredation(img, mt, mm, rng, cfg_edge, trace)

    cfg_elastic = aug_cfg.get("elastic_distortion", {})
    img, mt, mm = _apply_elastic_distortion(img, mt, mm, rng, cfg_elastic, trace)

    geom_M: Optional[np.ndarray] = None
    if chosen["geometry"]:
        rot0, rot1 = cfg_geom.get("rotation_deg", [-6.0, 6.0])
        rot = rng.uniform(float(rot0), float(rot1))

        cx, cy = W / 2.0, H / 2.0
        M2 = cv2.getRotationMatrix2D((cx, cy), rot, 1.0)
        M = np.eye(3, dtype=np.float32)
        M[:2, :] = M2

        pj0, pj1 = cfg_geom.get("perspective_jitter_ratio", [0.0, 0.03])
        jitter = rng.uniform(float(pj0), float(pj1)) * float(min(W, H))
        if float(jitter) > 0 and bool(meta.get("perspective", False)):
            src = np.float32([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]])
            dst = src + np.float32(
                [
                    [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                    [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                    [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                    [rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)],
                ]
            )
            P = cv2.getPerspectiveTransform(src, dst)
            M = P @ M

        geom_M = M.astype(np.float32)

        img = _warp(img, geom_M, (W, H), is_mask=False)
        mt = _warp(mt, geom_M, (W, H), is_mask=True)
        mm = _warp(mm, geom_M, (W, H), is_mask=True)

        trace.append({"op": "geometry", "rotation_deg": rot, "perspective": bool(meta.get("perspective", False))})

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

        for k, ln in enumerate(kept_lines):
            ln["global_line_order"] = k

        ann["lines"] = kept_lines

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

    mt = np.where(mt > 127, 255, 0).astype(np.uint8)
    mm = np.where(mm > 127, 255, 0).astype(np.uint8)

    _sync_meta_from_annotation_and_masks(ann, mt, mm)

    return AugResult(
        image_aug_u8=img,
        mask_text_aug_u8=mt,
        mask_math_aug_u8=mm,
        ann_aug=ann,
        aug_trace=trace,
        geom_M=geom_M,
    )