# src/docsynthfab/render/draw_utils.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12

from __future__ import annotations

import random
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont


def _pick_weighted(rng: random.Random, dist: Dict[str, float]) -> str:
    items = list(dist.items())
    if not items:
        return "latin"
    s = sum(max(0.0, float(p)) for _, p in items) or 1.0
    r = rng.random() * s
    acc = 0.0
    for k, p in items:
        acc += max(0.0, float(p))
        if r <= acc:
            return str(k)
    return str(items[-1][0])


def _sample_contrast_color(rng: random.Random, style_cfg: Dict[str, object]) -> Tuple[int, int, int]:
    """Sample a grayscale text color from the configured contrast distribution."""
    dist = style_cfg.get("contrast_class_dist", {"high": 0.7, "medium": 0.2, "low": 0.1})
    contrast_class = _pick_weighted(rng, dist)

    if contrast_class == "low":
        val = rng.randint(120, 170)
    elif contrast_class == "medium":
        val = rng.randint(60, 119)
    else:
        val = rng.randint(0, 59)

    return (val, val, val)


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> float:
    try:
        return float(draw.textlength(text, font=font))
    except Exception:
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return float(bbox[2] - bbox[0])
        except Exception:
            return float(len(text) * 10)


def _draw_text_glyph_mask(
    draw_img: ImageDraw.ImageDraw,
    draw_mask: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont,
    fill_rgb: Tuple[int, int, int] = (0, 0, 0),
) -> None:
    draw_img.text((x, y), text, fill=fill_rgb, font=font)
    draw_mask.text((x, y), text, fill=255, font=font)


def _paste_alpha_as_binary(mask_img_L: Image.Image, alpha_L: Image.Image, x: int, y: int) -> None:
    ww, hh = alpha_L.size
    mask_img_L.paste(255, (x, y, x + ww, y + hh), alpha_L)



