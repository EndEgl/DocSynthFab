# src/docsynthfab/render/figure_renderer.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - Pillow>=10,<12

from __future__ import annotations

import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def _make_random_figure_patch(rng: random.Random, ww: int, hh: int, family: str) -> Image.Image:
    seed_np = rng.randint(0, 2**32 - 1)
    np_rng = np.random.default_rng(seed_np)

    ww = max(1, int(ww))
    hh = max(1, int(hh))

    if ww < 16 or hh < 16:
        tiny = Image.new("RGB", (ww, hh), (245, 245, 245))
        d = ImageDraw.Draw(tiny)

        if ww > 2 and hh > 2:
            d.rectangle((0, 0, ww - 1, hh - 1), outline=(120, 120, 120), width=1)

        return tiny

    if family == "chart":
        im = Image.new("RGB", (ww, hh), (255, 255, 255))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, ww - 1, hh - 1), outline=(60, 60, 60), width=2)

        margin_x = max(8, ww // 12)
        margin_y = max(8, hh // 12)

        margin_x = min(margin_x, max(1, (ww - 12) // 2))
        margin_y = min(margin_y, max(1, (hh - 12) // 2))

        x_min = margin_x
        x_max = ww - margin_x
        y_min = margin_y + 5
        y_max = hh - margin_y - 5

        if x_min >= x_max or y_min > y_max or (ww < 40) or (hh < 30):
            pad_x = max(2, min(6, ww // 8))
            pad_y = max(2, min(6, hh // 8))

            d.line((pad_x, hh - pad_y, ww - pad_x, hh - pad_y), fill=(80, 80, 80), width=1)
            d.line((pad_x, pad_y, pad_x, hh - pad_y), fill=(80, 80, 80), width=1)

            if ww > 2 * pad_x + 4 and hh > 2 * pad_y + 4:
                pts = [
                    (pad_x, hh - pad_y - 1),
                    (max(pad_x + 1, ww // 3), max(pad_y, hh // 2)),
                    (max(pad_x + 2, 2 * ww // 3), max(pad_y, hh // 3)),
                    (ww - pad_x, max(pad_y, hh // 4)),
                ]

                for i in range(len(pts) - 1):
                    d.line(
                        (pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]),
                        fill=(30, 30, 30),
                        width=1,
                    )

            return im

        d.line((margin_x, hh - margin_y, ww - margin_x, hh - margin_y), fill=(80, 80, 80), width=2)
        d.line((margin_x, margin_y, margin_x, hh - margin_y), fill=(80, 80, 80), width=2)

        n = rng.randint(4, 8)
        pts = []
        usable_w = max(1, ww - 2 * margin_x)

        for i in range(n):
            x = margin_x + int(usable_w * i / max(1, n - 1))
            y = rng.randint(y_min, y_max)
            pts.append((x, y))

        for i in range(len(pts) - 1):
            d.line((pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]), fill=(30, 30, 30), width=2)

        for x, y in pts:
            r = max(1, min(4, min(ww, hh) // 20))
            d.ellipse((x - r, y - r, x + r, y + r), outline=(30, 30, 30), width=1)

        return im

    if family == "diagram":
        im = Image.new("RGB", (ww, hh), (255, 255, 255))
        d = ImageDraw.Draw(im)

        for _ in range(rng.randint(3, 6)):
            x0 = rng.randint(5, max(6, ww - 60))
            y0 = rng.randint(5, max(6, hh - 35))
            x1 = min(ww - 5, x0 + rng.randint(35, max(36, ww // 3)))
            y1 = min(hh - 5, y0 + rng.randint(20, max(21, hh // 4)))
            d.rectangle((x0, y0, x1, y1), outline=(50, 50, 50), width=2)

        for _ in range(rng.randint(2, 5)):
            x0 = rng.randint(5, ww - 5)
            y0 = rng.randint(5, hh - 5)
            x1 = rng.randint(5, ww - 5)
            y1 = rng.randint(5, hh - 5)
            d.line((x0, y0, x1, y1), fill=(70, 70, 70), width=2)

        return im

    if family == "texture":
        arr = np_rng.integers(0, 256, size=(hh, ww, 3), dtype=np.uint8)
        im = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=float(rng.uniform(0.6, 1.8))))
        d = ImageDraw.Draw(im)

        for _ in range(rng.randint(3, 8)):
            x0 = rng.randint(0, max(0, ww - 10))
            y0 = rng.randint(0, max(0, hh - 10))
            x1 = rng.randint(x0 + 5, min(ww, x0 + rng.randint(20, max(21, ww // 2))))
            y1 = rng.randint(y0 + 5, min(hh, y0 + rng.randint(20, max(21, hh // 2))))
            col = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))

            if rng.random() < 0.5:
                d.rectangle((x0, y0, x1, y1), outline=col, width=rng.randint(1, 4))
            else:
                d.ellipse((x0, y0, x1, y1), outline=col, width=rng.randint(1, 4))

        return im

    arr = np_rng.integers(40, 220, size=(hh, ww, 3), dtype=np.uint8)
    im = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=float(rng.uniform(0.8, 1.6))))
    d = ImageDraw.Draw(im)

    for _ in range(rng.randint(4, 10)):
        x0 = rng.randint(0, max(0, ww - 15))
        y0 = rng.randint(0, max(0, hh - 15))
        x1 = rng.randint(x0 + 5, min(ww, x0 + rng.randint(20, max(21, ww // 2))))
        y1 = rng.randint(y0 + 5, min(hh, y0 + rng.randint(20, max(21, hh // 2))))
        fill = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))

        if rng.random() < 0.5:
            d.rectangle((x0, y0, x1, y1), outline=fill, width=rng.randint(1, 3))
        else:
            d.ellipse((x0, y0, x1, y1), outline=fill, width=rng.randint(1, 3))

    return im



