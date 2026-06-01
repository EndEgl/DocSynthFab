# src/ai1_gen/render/font_utils.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12

from __future__ import annotations

import random
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from fontTools.ttLib import TTFont
from PIL import ImageFont

from .draw_utils import _measure_text



_SCRIPT_DIR_MAP: Dict[str, List[str]] = {
    "latin": ["latin", "mono"],
    "tr": ["latin", "mono"],
    "de": ["latin", "mono"],
    "ru": ["cyrillic", "mono"],
    "el": ["greek", "mono"],
    "ar": ["arabic"],
    "symbols": ["symbols", "mono"],
}

_ROLE_EXTRA_DIRS: Dict[str, List[str]] = {
    "body": [],
    "title": ["latin"],
    "caption": [],
    "table": ["mono"],
    "list": [],
    "code": ["mono"],
    "decorative": ["decorative"],
    "handwriting": ["handwriting"],
}


def _iter_font_files(folder: Path) -> List[Path]:
    out: List[Path] = []
    out.extend(sorted(folder.glob("*.ttf")))
    out.extend(sorted(folder.glob("*.otf")))
    out.extend(sorted(folder.glob("*.ttc")))
    return out


def _font_dirs_for_script_and_role(
    fonts_dir: str | None,
    script: str,
    role: str = "body",
) -> List[Path]:
    if not fonts_dir:
        return []

    root = Path(fonts_dir)
    if not root.exists():
        return []

    dir_names: List[str] = []
    dir_names.extend(_SCRIPT_DIR_MAP.get(script, ["latin"]))
    dir_names.extend(_ROLE_EXTRA_DIRS.get(role, []))

    seen = set()
    uniq: List[Path] = []

    for name in dir_names:
        if name in seen:
            continue
        seen.add(name)
        p = root / name
        if p.exists() and p.is_dir():
            uniq.append(p)

    for fallback_name in ["latin", "mono"]:
        p = root / fallback_name
        if p.exists() and p.is_dir() and p not in uniq:
            uniq.append(p)

    return uniq


def _font_candidates(
    fonts_dir: str | None,
    script: str,
    role: str = "body",
) -> List[Path]:
    dirs = _font_dirs_for_script_and_role(fonts_dir, script, role)
    out: List[Path] = []

    for d in dirs:
        out.extend(_iter_font_files(d))

    return out


_LAYOUT_CHARS = {" ", "\n", "\t", "\r"}


@lru_cache(maxsize=256)
def _font_codepoints(font_path_str: str) -> frozenset[int]:
    font = TTFont(font_path_str)
    codepoints: set[int] = set()

    try:
        for table in font["cmap"].tables:
            codepoints.update(table.cmap.keys())
    finally:
        font.close()

    return frozenset(codepoints)


def _missing_chars_for_font_path(font_path: Path, text: str) -> str:
    if not text:
        return ""

    required = {
        ord(ch)
        for ch in str(text)
        if ch not in _LAYOUT_CHARS
    }

    if not required:
        return ""

    try:
        supported = _font_codepoints(str(font_path.resolve()))
    except Exception:
        return "".join(chr(cp) for cp in sorted(required))

    missing = sorted(required - set(supported))
    return "".join(chr(cp) for cp in missing)




def _font_supports_text(font: ImageFont.ImageFont, text: str) -> bool:
    """Return False when a font is likely unable to render the provided text."""
    if not text:
        return True

    try:
        m = font.getmask(text)
        if m.getbbox() is None:
            return False
    except Exception:
        return False

    for ch in text:
        if ch.isspace():
            continue
        try:
            cm = font.getmask(ch)
            if cm.getbbox() is None:
                return False
        except Exception:
            return False

    return True


def _sample_probe_text_for_script(script: str, role: str = "body") -> str:
    if role == "title":
        if script == "tr":
            return "Başlık Örnek"
        if script == "de":
            return "Beispiel Titel"
        if script == "ru":
            return "Пример Заголовок"
        if script == "el":
            return "Παράδειγμα Τίτλος"
        if script == "ar":
            return "عنوان مثال"
        if script == "symbols":
            return "∑ ∞ √ ≤ ≥"
        return "Example Title"

    if role == "caption":
        if script == "tr":
            return "Şekil açıklaması"
        if script == "de":
            return "Abbildungslegende"
        if script == "ru":
            return "Подпись рисунка"
        if script == "el":
            return "Λεζάντα σχήματος"
        if script == "ar":
            return "شرح الشكل"
        if script == "symbols":
            return "≈ ≤ ≥ →"
        return "Figure caption"

    if role == "table":
        if script == "tr":
            return "veri 123"
        if script == "de":
            return "daten 123"
        if script == "ru":
            return "данные 123"
        if script == "el":
            return "δεδομένα 123"
        if script == "ar":
            return "بيانات 123"
        if script == "symbols":
            return "± × ÷ 123"
        return "data 123"

    if script == "tr":
        return "örnek çözüm veri satır"
    if script == "de":
        return "Beispiel Lösung Daten"
    if script == "ru":
        return "пример решение данные"
    if script == "el":
        return "παράδειγμα λύση δεδομένα"
    if script == "ar":
        return "مثال حل بيانات"
    if script == "symbols":
        return "± × ÷ ≤ ≥ √"

    return "example solution data line"


def _safe_font_for_text(
    fonts_dir: str | None,
    size: int,
    rng: random.Random,
    *,
    script: str = "latin",
    role: str = "body",
    probe_text: str | None = None,
) -> ImageFont.ImageFont:
    candidates = _font_candidates(fonts_dir, script=script, role=role)

    if probe_text is None:
        probe_text = _sample_probe_text_for_script(script, role)

    def _try_candidates(
        paths: List[Path],
        *,
        check_text: str,
        max_tries: int,
    ) -> ImageFont.ImageFont | None:
        if not paths:
            return None

        tries = min(max_tries, len(paths))
        sampled = paths[:] if len(paths) <= tries else rng.sample(paths, tries)

        for path in sampled:
            try:
                # Strong glyph coverage check via fontTools/cmap.
                if _missing_chars_for_font_path(path, check_text):
                    continue

                fnt = ImageFont.truetype(str(path), size=size)

                # Pillow-level sanity check.
                if _font_supports_text(fnt, check_text):
                    return fnt

            except Exception:
                continue

        return None

    # 1. Preferred script/role-specific candidates.
    selected = _try_candidates(
        candidates,
        check_text=probe_text,
        max_tries=12,
    )
    if selected is not None:
        return selected

    # 2. Latin fallback only when the requested script is not latin.
    # Important: still check against the original probe_text. If the text is
    # Cyrillic/Arabic/Greek, a Latin-only font will be rejected here.
    if script != "latin":
        latin_candidates = _font_candidates(fonts_dir, script="latin", role=role)
        selected = _try_candidates(
            latin_candidates,
            check_text=probe_text,
            max_tries=10,
        )
        if selected is not None:
            return selected

    # 3. Mono fallback, still checked against the same text.
    mono_candidates = _font_candidates(fonts_dir, script="latin", role="code")
    selected = _try_candidates(
        mono_candidates,
        check_text=probe_text,
        max_tries=8,
    )
    if selected is not None:
        return selected

    # 4. Last-resort PIL default. This may not support the text, but prevents
    # the pipeline from crashing if no font files are configured.
    return ImageFont.load_default()



def _safe_font(fonts_dir: str | None, size: int, rng: random.Random) -> ImageFont.ImageFont:
    """Backward-compatible default font selector."""
    return _safe_font_for_text(
        fonts_dir,
        size=size,
        rng=rng,
        script="latin",
        role="body",
        probe_text="example data line",
    )


def _font_height_px(font: ImageFont.ImageFont) -> int:
    try:
        ascent, descent = font.getmetrics()
        return int((ascent + descent) * 1.20)
    except Exception:
        return 14


def _fit_font_to_bbox_height(
    fonts_dir: str | None,
    desired_size: int,
    bbox_h: int,
    rng: random.Random,
    *,
    script: str = "latin",
    role: str = "body",
    probe_text: str | None = None,
) -> ImageFont.ImageFont:
    max_size = max(8, int(bbox_h * 0.78))
    size = max(8, min(int(desired_size), int(max_size)))

    return _safe_font_for_text(
        fonts_dir,
        size=size,
        rng=rng,
        script=script,
        role=role,
        probe_text=probe_text,
    )