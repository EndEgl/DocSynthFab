# src/docsynthfab/augment/policy.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

import random
from typing import Any, Dict


def sample_policy(rng: random.Random, pol: Dict[str, float]) -> Dict[str, bool]:
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


def context_adjust_policy(meta: Dict[str, Any], pol: Dict[str, float]) -> Dict[str, float]:
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


def build_aug_plan(
    meta: Dict[str, Any],
    aug_cfg: Dict[str, Any],
    rng: random.Random,
) -> Dict[str, bool]:
    selpol = aug_cfg.get("selection_policy", {})
    noise_level = str(meta.get("noise_level", "clean"))

    base_pol = selpol.get(noise_level, selpol.get("clean", {}))
    pol = context_adjust_policy(meta, base_pol)
    chosen = sample_policy(rng, pol)

    if chosen["edge"] and chosen["elastic"]:
        if rng.random() < 0.5:
            chosen["elastic"] = False
        else:
            chosen["edge"] = False

    if chosen["capture"] and chosen["geometry"] and rng.random() < 0.35:
        chosen["geometry"] = False

    return chosen



