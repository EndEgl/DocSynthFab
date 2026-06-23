# src/docsynthfab/render/font_utils.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12

from __future__ import annotations

import random
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from fontTools.ttLib import TTFont, TTCollection
from PIL import ImageFont

from .draw_utils import _measure_text



_SCRIPT_DIR_MAP: Dict[str, List[str]] = {
    # Latin-script languages
    "latin": ["latin", "mono"],
    "en": ["latin", "mono"],
    "tr": ["latin", "mono"],
    "de": ["latin", "mono"],
    "es": ["latin", "mono"],
    "fr": ["latin", "mono"],

    # Cyrillic / Greek / Arabic
    "cyrillic": ["cyrillic", "mono"],
    "ru": ["cyrillic", "mono"],

    "greek": ["greek", "mono"],
    "el": ["greek", "mono"],

    "arabic": ["arabic"],
    "ar": ["arabic"],

    # Hebrew
    "hebrew": ["hebrew"],
    "he": ["hebrew"],

    # Devanagari / Hindi
    "devanagari": ["devanagari"],
    "hi": ["devanagari"],

    # CJK / Han / Japanese
    "cjk": ["cjk"],
    "han": ["cjk"],
    "zh": ["cjk"],
    "ja": ["cjk"],
    "kana_han": ["cjk"],

    # Korean
    "hangul": ["hangul"],
    "ko": ["hangul"],

    # Thai
    "thai": ["thai"],
    "th": ["thai"],

    # Symbols / mono
    "symbols": ["symbols", "mono"],
    "mono": ["mono"],
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

_SCRIPT_ALIAS_MAP: Dict[str, str] = {
    "en": "latin",
    "tr": "latin",
    "de": "latin",
    "es": "latin",
    "fr": "latin",
    "cyrillic": "ru",
    "greek": "el",
    "arabic": "ar",
    "hebrew": "he",
    "devanagari": "hi",
    "cjk": "zh",
    "han": "zh",
    "kana_han": "ja",
    "hangul": "ko",
    "thai": "th",
}


def _normalize_script_name(script: str) -> str:
    s = str(script or "latin").strip().lower()
    return _SCRIPT_ALIAS_MAP.get(s, s)


def _system_font_candidates_for_script(script: str) -> List[Path]:
    """
    Prefer OS fonts for scripts that often render as tofu boxes when routed
    through generic Latin/mono fonts.
    """
    script = _normalize_script_name(script)

    win = Path("C:/Windows/Fonts")
    if not win.exists():
        return []

    names_by_script: Dict[str, List[str]] = {
        # Chinese
        "zh": [
            "msyh.ttc",
            "msyhbd.ttc",
            "msyhl.ttc",
            "simsun.ttc",
            "simsunb.ttf",
            "SimsunExtG.ttf",
        ],

        # Japanese
        "ja": [
            "YuGothR.ttc",
            "YuGothM.ttc",
            "YuGothB.ttc",
            "YuGothL.ttc",
            "msgothic.ttc",
        ],

        # Korean
        "ko": [
            "malgun.ttf",
            "malgunbd.ttf",
            "malgunsl.ttf",
        ],

        # Thai
        "th": [
            "Nirmala.ttc",
        ],

        # Hebrew
        "he": [
            "arial.ttf",
            "arialbd.ttf",
        ],

        # Hindi / Devanagari
        "hi": [
            "Nirmala.ttc",
        ],

        # Arabic
        "ar": [
            "arial.ttf",
            "arialbd.ttf",
            "Nirmala.ttc",
        ],

        # Russian / Greek usually okay with Arial too.
        "ru": [
            "arial.ttf",
            "arialbd.ttf",
        ],
        "el": [
            "arial.ttf",
            "arialbd.ttf",
        ],
    }

    out: List[Path] = []
    for name in names_by_script.get(script, []):
        p = win / name
        if p.exists() and p.is_file():
            out.append(p)

    return out


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
    script = _normalize_script_name(script)

    dirs = _font_dirs_for_script_and_role(fonts_dir, script, role)
    out: List[Path] = []

    # Prefer bundled project fonts first.
    # This keeps DocSynthFab reproducible and avoids Windows font differences.
    for d in dirs:
        out.extend(_iter_font_files(d))

    def _score_font_path(p: Path) -> int:
        name = p.name.lower()

        if script == "zh":
            if "notosanssc" in name or "sc" in name or "hans" in name or "simplified" in name:
                return 0
            if "notosansjp" in name or "jp" in name:
                return 10
            if "latin" in str(p).lower():
                return 80
            if "mono" in str(p).lower():
                return 90
            return 30

        if script == "ja":
            if "notosansjp" in name or "jp" in name:
                return 0
            if "notosanssc" in name or "sc" in name or "hans" in name or "simplified" in name:
                return 10
            if "latin" in str(p).lower():
                return 80
            if "mono" in str(p).lower():
                return 90
            return 30


        if script == "ko":
            if "notosanskr" in name or "kr" in name:
                return 0
            return 20

        if script == "hi":
            if "devanagari" in name:
                return 0
            return 20

        if script == "th":
            if "thai" in name:
                return 0
            return 20

        if script == "he":
            if "hebrew" in name:
                return 0
            return 20

        if script == "ar":
            if "arabic" in name:
                return 0
            return 20

        if script in {"latin", "tr", "de", "es", "fr", "en"}:
            if "notosans-regular" in name:
                return 0
            if "mono" in name:
                return 40
            return 10

        if script == "ru":
            if "notosans-regular" in name:
                return 0
            return 10

        if script == "el":
            if "notosans-regular" in name:
                return 0
            return 10

        return 10

    out = sorted(out, key=_score_font_path)

    # Stable de-duplication.
    seen: set[str] = set()
    uniq: List[Path] = []
    for p in out:
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)

    return uniq

_LAYOUT_CHARS = {" ", "\n", "\t", "\r"}


@lru_cache(maxsize=256)
def _font_codepoints(font_path_str: str) -> frozenset[int]:
    path = Path(font_path_str)
    codepoints: set[int] = set()

    if path.suffix.lower() == ".ttc":
        collection = TTCollection(str(path))
        try:
            for font in collection.fonts:
                try:
                    if "cmap" not in font:
                        continue
                    for table in font["cmap"].tables:
                        codepoints.update(table.cmap.keys())
                except Exception:
                    continue
        finally:
            try:
                collection.close()
            except Exception:
                pass

        return frozenset(codepoints)

    font = TTFont(str(path))
    try:
        if "cmap" in font:
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
    script = str(script or "latin").strip().lower()
    role = str(role or "body").strip().lower()

    # Normalize aliases used by text_synth / config.
    alias_map = {
        "en": "latin",
        "es": "latin",
        "fr": "latin",
        "cyrillic": "ru",
        "greek": "el",
        "arabic": "ar",
        "hebrew": "he",
        "devanagari": "hi",
        "cjk": "zh",
        "han": "zh",
        "kana_han": "ja",
        "hangul": "ko",
        "thai": "th",
    }
    script = alias_map.get(script, script)

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
        if script == "he":
            return "כותרת לדוגמה"
        if script == "hi":
            return "उदाहरण शीर्षक"
        if script == "zh":
            return "示例标题"
        if script == "ja":
            return "サンプル見出し"
        if script == "ko":
            return "예시 제목"
        if script == "th":
            return "หัวข้อตัวอย่าง"
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
        if script == "he":
            return "כיתוב איור"
        if script == "hi":
            return "चित्र विवरण"
        if script == "zh":
            return "图像说明"
        if script == "ja":
            return "図の説明"
        if script == "ko":
            return "그림 설명"
        if script == "th":
            return "คำอธิบายภาพ"
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
        if script == "he":
            return "נתונים 123"
        if script == "hi":
            return "डेटा 123"
        if script == "zh":
            return "数据 123"
        if script == "ja":
            return "データ 123"
        if script == "ko":
            return "데이터 123"
        if script == "th":
            return "ข้อมูล 123"
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
    if script == "he":
        return "דוגמה פתרון נתונים"
    if script == "hi":
        return "उदाहरण समाधान डेटा"
    if script == "zh":
        return "示例 解决 数据"
    if script == "ja":
        return "例 解決 データ"
    if script == "ko":
        return "예시 해결 데이터"
    if script == "th":
        return "ตัวอย่าง ข้อมูล"
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

                if path.suffix.lower() == ".ttc":
                    loaded_fonts = []

                    for font_index in range(0, 12):
                        try:
                            fnt = ImageFont.truetype(
                                str(path),
                                size=size,
                                index=font_index,
                            )

                            try:
                                setattr(fnt, "_docsynthfab_font_path", str(path))
                                setattr(fnt, "_docsynthfab_font_index", int(font_index))
                            except Exception:
                                pass

                            loaded_fonts.append(fnt)

                        except Exception:
                            continue
                else:
                    fnt = ImageFont.truetype(str(path), size=size)

                    try:
                        setattr(fnt, "_docsynthfab_font_path", str(path))
                        setattr(fnt, "_docsynthfab_font_index", 0)
                    except Exception:
                        pass

                    loaded_fonts = [fnt]

                for fnt in loaded_fonts:
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
    fallback_font = ImageFont.load_default()

    try:
        setattr(fallback_font, "_docsynthfab_font_path", "__PIL_DEFAULT__")
        setattr(fallback_font, "_docsynthfab_font_index", -1)
    except Exception:
        pass

    return fallback_font



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
    # Tiny OCR lines can be 6-8 px high in dpi200 sparse pages.
    # Do not force min 8 px, otherwise small valid lines are skipped or overflow.
    max_size = max(6, int(bbox_h * 0.95))
    size = max(6, min(int(desired_size), int(max_size)))

    return _safe_font_for_text(
        fonts_dir,
        size=size,
        rng=rng,
        script=script,
        role=role,
        probe_text=probe_text,
    )


