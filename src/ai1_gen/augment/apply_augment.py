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
import copy

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

    # -------------------------------------------------
    # 1) Blur: biraz daha seyrek ama doğal
    # -------------------------------------------------
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

    # -------------------------------------------------
    # 2) Speckle: tüm sayfaya eşit değil, hafif
    # -------------------------------------------------
    if rng.random() < 0.35:
        sp_range = cfg.get("speckle", [0.006, 0.028])
        sp = rng.uniform(float(sp_range[0]), float(sp_range[1]))
        n = np_rng.normal(loc=0.0, scale=float(sp) * 255.0, size=out.shape).astype(np.float32)
        out_f = out.astype(np.float32) + n
        out = np.clip(out_f, 0, 255).astype(np.uint8)
        trace.append({"op": "speckle_noise", "amount": sp})

    # -------------------------------------------------
    # 3) Düz çizgiler yerine düzensiz streak / scratch
    # -------------------------------------------------
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
            cv2.line(overlay, (x0, y0), (x1, y1), color, thickness=thickness, lineType=cv2.LINE_AA)

            alpha = rng.uniform(0.08, 0.28)
            out = cv2.addWeighted(overlay, alpha, out, 1.0 - alpha, 0.0)

            applied.append({
                "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                "thickness": thickness, "alpha": alpha
            })

        trace.append({"op": "irregular_scratches", "count": num_scratches, "items": applied[:5]})

    # -------------------------------------------------
    # 4) Lokal kir/li leke blob'ları
    # -------------------------------------------------
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
        out = np.clip(out.astype(np.float32) * (1.0 - blob_mask_f * (1.0 - darken)), 0, 255).astype(np.uint8)

        trace.append({"op": "dirty_blobs", "count": num_blobs, "darken": darken})

    # -------------------------------------------------
    # 5) Tek gradient yerine low-frequency aydınlatma düzensizliği
    # -------------------------------------------------
    if rng.random() < 0.24:
        small_w = max(8, w // rng.randint(18, 36))
        small_h = max(8, h // rng.randint(18, 36))

        illum_small = np_rng.uniform(0.0, 1.0, (small_h, small_w)).astype(np.float32)
        illum_small = cv2.GaussianBlur(illum_small, (0, 0), sigmaX=rng.uniform(2.0, 5.0))
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

    # -------------------------------------------------
    # 6) Düz scanner streak yerine düzensiz yatay/dikey banding
    # -------------------------------------------------
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

            out = np.clip((1.0 - alpha) * out.astype(np.float32) + alpha * band_overlay, 0, 255).astype(np.uint8)

        trace.append({"op": "irregular_banding", "count": num_bands})

    # -------------------------------------------------
    # 7) Salt-pepper daha nadir ve daha asimetrik
    # -------------------------------------------------
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
        "edge": _b(pol.get("p_edge", 0.08)),
        "elastic": _b(pol.get("p_elastic", 0.04)),
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
        img, x_map, y_map, cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255)
    )
    distorted_mt = cv2.remap(
        mt, x_map, y_map, cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0
    )
    distorted_mm = cv2.remap(
        mm, x_map, y_map, cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0
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


def _context_adjust_policy(meta: Dict[str, Any], pol: Dict[str, float]) -> Dict[str, float]:
    out = dict(pol)

    has_equation = bool(meta.get("has_equation", False))
    has_table = bool(meta.get("has_table", False))
    scale_profile = str(meta.get("scale_profile", "dpi300"))
    density_level = str(meta.get("density_level", "normal"))

    if has_equation:
        out["p_edge"] = min(float(out.get("p_edge", 0.08)), 0.04)
        out["p_elastic"] = min(float(out.get("p_elastic", 0.04)), 0.02)
        out["p_geometry"] = min(float(out.get("p_geometry", 0.10)), 0.08)

    if has_table:
        out["p_elastic"] = min(float(out.get("p_elastic", 0.04)), 0.01)
        out["p_geometry"] = min(float(out.get("p_geometry", 0.10)), 0.06)
        out["p_edge"] = min(float(out.get("p_edge", 0.08)), 0.03)

    if density_level in {"dense", "very_dense"}:
        out["p_blur_noise"] = min(float(out.get("p_blur_noise", 0.25)), 0.18)

    if scale_profile == "lowres_capture":
        out["p_capture"] = max(float(out.get("p_capture", 0.15)), 0.60)
        out["p_blur_noise"] = min(float(out.get("p_blur_noise", 0.25)), 0.15)

    return out


def _build_aug_plan(meta: Dict[str, Any], aug_cfg: Dict[str, Any], rng: random.Random) -> Dict[str, bool]:
    selpol = aug_cfg.get("selection_policy", {})
    noise_level = str(meta.get("noise_level", "clean"))
    base_pol = selpol.get(noise_level, selpol.get("clean", {}))
    pol = _context_adjust_policy(meta, base_pol)
    chosen = _sample_policy(rng, pol)

    # structural budget: edge ve elastic aynı anda gelmesin
    if chosen["edge"] and chosen["elastic"]:
        if rng.random() < 0.5:
            chosen["elastic"] = False
        else:
            chosen["edge"] = False

    # capture varsa structural biraz kıs
    if chosen["capture"] and chosen["geometry"] and rng.random() < 0.35:
        chosen["geometry"] = False

    return chosen


def _quick_quality_gate(
    before_mt: np.ndarray,
    before_mm: np.ndarray,
    after_mt: np.ndarray,
    after_mm: np.ndarray,
    meta: Dict[str, Any],
) -> Tuple[bool, Dict[str, float]]:
    bt = max(1, int(np.count_nonzero(before_mt)))
    at = int(np.count_nonzero(after_mt))
    bm = int(np.count_nonzero(before_mm))
    am = int(np.count_nonzero(after_mm))

    text_ratio = at / bt
    math_ratio = 1.0 if bm == 0 else (am / max(1, bm))

    has_equation = bool(meta.get("has_equation", False))
    ok = text_ratio >= 0.72 and (not has_equation or math_ratio >= 0.82)

    return ok, {
        "text_area_ratio": float(text_ratio),
        "math_area_ratio": float(math_ratio),
        "before_text_nz": float(bt),
        "after_text_nz": float(at),
        "before_math_nz": float(bm),
        "after_math_nz": float(am),
    }


def _apply_geometry_and_update_ann(
    img: np.ndarray,
    mt: np.ndarray,
    mm: np.ndarray,
    ann: Dict[str, Any],
    meta: Dict[str, Any],
    aug_cfg: Dict[str, Any],
    rng: random.Random,
    trace: List[Dict[str, Any]],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any], Optional[np.ndarray]]:
    H, W = img.shape[:2]
    cfg_geom = aug_cfg.get("geometry", {})

    rot0, rot1 = cfg_geom.get("rotation_deg", [-6.0, 6.0])

    if bool(meta.get("has_equation", False)):
        rot0, rot1 = max(-4.0, float(rot0)), min(4.0, float(rot1))
    if bool(meta.get("has_table", False)):
        rot0, rot1 = max(-3.0, float(rot0)), min(3.0, float(rot1))

    rot = rng.uniform(float(rot0), float(rot1))

    cx, cy = W / 2.0, H / 2.0
    M2 = cv2.getRotationMatrix2D((cx, cy), rot, 1.0)
    M = np.eye(3, dtype=np.float32)
    M[:2, :] = M2

    pj0, pj1 = cfg_geom.get("perspective_jitter_ratio", [0.0, 0.03])
    if bool(meta.get("has_table", False)):
        pj1 = min(float(pj1), 0.015)
    elif bool(meta.get("has_equation", False)):
        pj1 = min(float(pj1), 0.02)

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
    return img, mt, mm, ann, geom_M


def apply_augment(
    image_u8: np.ndarray,
    mask_text_u8: np.ndarray,
    mask_math_u8: np.ndarray,
    ann: Dict[str, Any],
    meta: Dict[str, Any],
    aug_cfg: Dict[str, Any],
    rng: random.Random,
) -> AugResult:
    trace: List[Dict[str, Any]] = []

    # input korunur
    img = image_u8.copy()
    mt = mask_text_u8.copy()
    mm = mask_math_u8.copy()
    ann_work = copy.deepcopy(ann)

    before_mt = mt.copy()
    before_mm = mm.copy()

    chosen = _build_aug_plan(meta, aug_cfg, rng)

    scale_profile = str(meta.get("scale_profile", "dpi300"))
    if scale_profile == "lowres_capture" and not chosen["capture"]:
        chosen["capture"] = True
        trace.append({
            "op": "policy_enforce",
            "reason": "lowres_required_missing",
            "code": "aug/lowres-required-missing",
        })

    cfg_photo = aug_cfg.get("photometric", {})
    cfg_blur = aug_cfg.get("blur_noise", {})
    cfg_capture = aug_cfg.get("capture_sim", {})
    cfg_edge = aug_cfg.get("edge_degredation", {})
    cfg_elastic = aug_cfg.get("elastic_distortion", {})

    noise_level = str(meta.get("noise_level", "clean"))

    if chosen["photometric"]:
        img = _apply_photometric(img, rng, cfg_photo, trace)

    if chosen["blur_noise"]:
        img = _apply_blur_noise(img, rng, cfg_blur, trace)

    if chosen["capture"]:
        img = _apply_capture_sim(img, rng, cfg_capture, noise_level, trace)

    if chosen["edge"]:
        img, mt, mm = _apply_edge_degredation(img, mt, mm, rng, cfg_edge, trace)

    if chosen["elastic"]:
        img, mt, mm = _apply_elastic_distortion(img, mt, mm, rng, cfg_elastic, trace)

    geom_M: Optional[np.ndarray] = None
    if chosen["geometry"]:
        img, mt, mm, ann_work, geom_M = _apply_geometry_and_update_ann(
            img, mt, mm, ann_work, meta, aug_cfg, rng, trace
        )

    mt = np.where(mt > 127, 255, 0).astype(np.uint8)
    mm = np.where(mm > 127, 255, 0).astype(np.uint8)

    ok, gate_metrics = _quick_quality_gate(before_mt, before_mm, mt, mm, meta)
    trace.append({"op": "quick_quality_gate", **gate_metrics, "accepted": bool(ok)})

    if not ok:
        # hafif fallback: yalnızca tone/capture ile dön
        trace.append({"op": "fallback_to_light_plan"})
        img = image_u8.copy()
        mt = mask_text_u8.copy()
        mm = mask_math_u8.copy()
        ann_work = copy.deepcopy(ann)
        geom_M = None

        if chosen["photometric"]:
            img = _apply_photometric(img, rng, cfg_photo, trace)
        if chosen["capture"]:
            img = _apply_capture_sim(img, rng, cfg_capture, noise_level, trace)

        mt = np.where(mt > 127, 255, 0).astype(np.uint8)
        mm = np.where(mm > 127, 255, 0).astype(np.uint8)

    _sync_meta_from_annotation_and_masks(ann_work, mt, mm)

    return AugResult(
        image_aug_u8=img,
        mask_text_aug_u8=mt,
        mask_math_aug_u8=mm,
        ann_aug=ann_work,
        aug_trace=trace,
        geom_M=geom_M,
    )