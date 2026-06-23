# src/docsynthfab/cli/fallback.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from .metadata import sync_ann_meta_from_masks


def make_fallback_render(cfg: Any, page_id: str, dpi: int = 300) -> Dict[str, Any]:
    if dpi >= 300:
        w, h = 2481, 3507
        scale_profile = "dpi300"
    else:
        w, h = 1654, 2339
        scale_profile = "dpi200"

    page_cfg = (cfg.raw.get("page", {}) or {}) if hasattr(cfg, "raw") else {}
    bg_color = page_cfg.get("bg_color_rgb", [255, 255, 255]) or [255, 255, 255]
    bg = tuple(int(x) for x in bg_color[:3])

    img = np.full((h, w, 3), bg, dtype=np.uint8)
    mt = np.zeros((h, w), dtype=np.uint8)
    mm = np.zeros((h, w), dtype=np.uint8)

    x0, y0 = 120, 180
    box = max(220, min(w, h) // 8)
    x1, y1 = x0 + box, y0 + box

    mt[y0:y1, x0:x1] = 255
    img[y0:y1, x0:x1, :] = 0

    ann: Dict[str, Any] = {
        "version": getattr(cfg, "version", "docsynthfab-ds-v0.1"),
        "page_id": page_id,
        "size": {"w": int(w), "h": int(h), "dpi": int(dpi)},
        "meta": {
            "layout_type": "single_col",
            "density_level": "sparse",
            "scale_profile": scale_profile,
            "noise_level": "clean",
            "has_table": False,
            "has_equation": False,
            "has_figure": False,
            "_fallback": True,
        },
        "gt_page_text": "FALLBACK_PAGE",
        "lines": [
            {
                "line_id": 0,
                "block_id": 0,
                "line_type": "text",
                "line_order_in_block": 0,
                "global_line_order": 0,
                "bbox": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)],
                "quad": None,
                "is_hard": False,
                "gt_text": "FALLBACK_PAGE",
                "gt_script": "latin",
            }
        ],
        "blocks": [],
        "gt_stats": {},
    }

    sync_ann_meta_from_masks(ann, mt, mm)

    return {
        "image_u8": img,
        "mask_text_u8": mt,
        "mask_math_u8": mm,
        "ann": ann,
    }


_make_fallback_render = make_fallback_render



