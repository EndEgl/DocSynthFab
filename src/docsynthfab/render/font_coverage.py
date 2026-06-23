# src/docsynthfab/render/font_coverage.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12
#
# Font render coverage smoke checks.
# This does NOT decide whether a word belongs to a language. It only checks
# whether the configured font can render the supplied text without crashing and
# without producing an empty mask.

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, List

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class FontCoverageItem:
    text: str
    ok: bool
    reason: str
    bbox: tuple[int, int, int, int] | None = None


@dataclass(frozen=True)
class FontCoverageReport:
    font_path: str
    total: int
    ok: int
    failed: int
    items: list[FontCoverageItem]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_font(font_path: str | Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(font_path), size=size)


def check_font_text(
    *,
    font_path: str | Path,
    text: str,
    size: int = 32,
    canvas: tuple[int, int] = (512, 128),
) -> FontCoverageItem:
    text = str(text or "")

    if not text.strip():
        return FontCoverageItem(text=text, ok=False, reason="empty-text")

    try:
        font = _load_font(font_path, size)
    except Exception as e:
        return FontCoverageItem(text=text, ok=False, reason=f"font-load-failed:{type(e).__name__}")

    try:
        img = Image.new("L", canvas, 0)
        draw = ImageDraw.Draw(img)

        try:
            bbox = draw.textbbox((8, 8), text, font=font)
        except Exception:
            bbox = None

        draw.text((8, 8), text, font=font, fill=255)

        rendered_bbox = img.getbbox()
        if rendered_bbox is None:
            return FontCoverageItem(text=text, ok=False, reason="empty-render", bbox=bbox)

        # Some missing glyphs render as boxes/tofu. Tofu detection is font-dependent,
        # so this smoke checker reports hard failures only: load/render/empty.
        return FontCoverageItem(text=text, ok=True, reason="ok", bbox=rendered_bbox)

    except Exception as e:
        return FontCoverageItem(text=text, ok=False, reason=f"render-failed:{type(e).__name__}")


def check_font_coverage(
    *,
    font_path: str | Path,
    texts: Iterable[str],
    size: int = 32,
    limit: int | None = None,
) -> FontCoverageReport:
    items: List[FontCoverageItem] = []

    for idx, text in enumerate(texts):
        if limit is not None and idx >= limit:
            break
        items.append(check_font_text(font_path=font_path, text=text, size=size))

    ok = sum(1 for item in items if item.ok)
    failed = len(items) - ok

    return FontCoverageReport(
        font_path=str(font_path),
        total=len(items),
        ok=ok,
        failed=failed,
        items=items,
    )




