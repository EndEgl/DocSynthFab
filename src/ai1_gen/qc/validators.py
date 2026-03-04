# src/ai1_gen/qc/validators.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

from typing import Any, Dict, Tuple
import numpy as np


def _is_binary_u8(mask: np.ndarray) -> bool:
    if mask.dtype != np.uint8:
        return False
    # DAHA GÜVENLİ VE HIZLI: np.unique yerine np.isin kullanımı (Performans iyileştirmesi)
    return bool(np.all(np.isin(mask, [0, 255])))


def compute_density_metrics(mask_text: np.ndarray, mask_math: np.ndarray) -> Dict[str, Any]:
    ink_text = float(np.mean(mask_text > 0))
    ink_math = float(np.mean(mask_math > 0))
    return {"ink_ratio_text": ink_text, "ink_ratio_math": ink_math}


def mixed_band_variance(mask_text: np.ndarray, bands: int) -> float:
    h = mask_text.shape[0]
    bs = max(1, h // bands)
    ratios = []
    for i in range(bands):
        y0 = i * bs
        y1 = h if i == bands - 1 else (i + 1) * bs
        band = mask_text[y0:y1, :]
        ratios.append(float(np.mean(band > 0)))
    return float(np.var(np.array(ratios, dtype=np.float32)))


def validate_page(ann: Dict[str, Any], mask_text: np.ndarray, mask_math: np.ndarray, cfg) -> Tuple[bool, str | None, Dict[str, Any]]:
    qc_cfg = cfg.qc()
    thr = cfg.thresholds()

    # 1. Mask Binary Kontrolü (Madde 1.2)
    if bool(qc_cfg.get("mask_binary_required", True)):
        if not _is_binary_u8(mask_text) or not _is_binary_u8(mask_math):
            return False, "qc/mask-not-binary", {}

    # 2. Çakışma Kontrolü (Madde 1.2: < 1%)
    overlap = np.logical_and(mask_text > 0, mask_math > 0)
    # GÜVENLİK: Eğer mask_text tamamen boşsa (0 piksel), sıfıra bölünme hatasını engellemek için max(1, ...) kullanıyoruz.
    text_pixels = max(1, int(np.sum(mask_text > 0)))
    overlap_ratio = float(np.sum(overlap)) / float(text_pixels)
    if overlap_ratio >= float(qc_cfg.get("overlap_text_over_math_max_ratio", 0.01)):
        return False, "qc/overlap-too-high", {"overlap_ratio": overlap_ratio}

    # 3. Global Line Order Kontrolü (Madde 7)
    if bool(qc_cfg.get("require_global_line_order_contiguous", True)):
        lines = ann.get("lines", [])
        for i, ln in enumerate(lines):
            if int(ln.get("global_line_order", -1)) != i:
                # Hata durumunda beklenen ve bulunan değeri ekstra olarak döndür (Testler için faydalı)
                return False, "qc/order-not-contiguous", {"expected": i, "found": ln.get("global_line_order")}

    meta = ann.get("meta", {})
    density_level = str(meta.get("density_level", "normal"))

    m = compute_density_metrics(mask_text, mask_math)
    ink = float(m["ink_ratio_text"])

    # 4. Density Range Kontrolü (Madde 2.3)
    ranges = thr.get("ink_ratio_text_ranges", {})
    if density_level in ranges:
        lo, hi = ranges[density_level]
        if not (float(lo) <= ink <= float(hi)):
            return False, "qc/density-out-of-range", {"ink_ratio_text": ink, "expected": [float(lo), float(hi)]}

    # 5. Mixed Sayfalar için Varyans Kontrolü (Madde 2.4)
    if density_level == "mixed":
        mb = thr.get("mixed", {})
        bands = int(mb.get("bands", 8))
        vthr = float(mb.get("variance_thr", 0.00015))
        v = mixed_band_variance(mask_text, bands=bands)
        if v <= vthr:
            return False, "qc/mixed-variance-too-low", {"var": v, "thr": vthr}

    # 6. Scale Profile ve DPI Uyum Kontrolü (Madde 3.1 & 5.5)
    scale_profile = str(meta.get("scale_profile", "dpi300"))
    dpi = int(ann.get("size", {}).get("dpi", 300))
    if scale_profile == "dpi200" and dpi != 200:
        return False, "qc/scale-profile-mismatch", {"scale_profile": scale_profile, "dpi": dpi}
    if scale_profile == "dpi300" and dpi != 300:
        return False, "qc/scale-profile-mismatch", {"scale_profile": scale_profile, "dpi": dpi}

    return True, None, {"overlap_ratio": overlap_ratio, **m}