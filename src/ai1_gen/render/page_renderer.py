# src/ai1_gen/render/page_renderer.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - Pillow>=10,<12

from __future__ import annotations

from typing import Any, Dict, Tuple, List, Optional
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from ai1_gen.layout.layout_sampler import PageSpec
from ai1_gen.latex.miktex_render import (
    render_latex_to_rgba,
    LatexRenderError,
    sample_latex_expr,
)

# -------------------------
# UTF-8 Text Synth
# -------------------------

_WORDS_LATIN = [
    "lorem", "ipsum", "dolor", "amet", "elit", "tempor", "incididunt",
    "data", "model", "train", "valid", "test", "loss", "accuracy",
]
_WORDS_TR = [
    "merhaba", "dünya", "örnek", "çözüm", "görsel", "metin", "yoğunluk",
    "ölçek", "doğrulama", "kalite", "veri", "çıktı", "süreç", "satır",
]
_WORDS_DE = [
    "Beispiel", "Lösung", "Wahrscheinlichkeit", "Zufall", "Gleichung",
    "Daten", "Modell", "Prüfung", "Ausgabe",
]
_WORDS_RU = ["пример", "решение", "данные", "модель", "строка", "качество"]
_WORDS_EL = ["παράδειγμα", "λύση", "δεδομένα", "μοντέλο"]
_WORDS_AR = ["مثال", "حل", "بيانات", "نموذج", "سطر"]

_LATIN_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_TR_EXTRA = "çÇğĞıİöÖşŞüÜ"
_DE_EXTRA = "äÄöÖüÜß"
_DIGITS = "0123456789"
_PUNCT = ".,;:!?()[]{}<>+-=*/_~'\"@#&%$"

_CYR_START, _CYR_END = 0x0410, 0x044F
_GR_START, _GR_END = 0x0391, 0x03C9
_AR_START, _AR_END = 0x0621, 0x064A

_SYMBOLS = "±×÷≤≥≈≠∑∏√∞∂∇∈∉∩∪→←↔°"

_BAR_CHARS = "█▓▒░▮▯▰▱▁▂▃▄▅▆▇─━═—–·•▪▫"
_CODE_OPS = ["==", "!=", "<=", ">=", "->", "::", "=>", "&&", "||", "+=", "-=", "*=", "/="]
_BULLETS = ["•", "-", "–", "—", "◦", "▪", "→"]


# -------------------------
# Font routing / coverage
# -------------------------

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


def _rand_from_range(rng: random.Random, a: int, b: int, k: int) -> str:
    return "".join(chr(rng.randint(a, b)) for _ in range(k))


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

def _sample_contrast_color(rng: random.Random, style_cfg: Dict[str, Any]) -> Tuple[int, int, int]:
    """
    Config'teki contrast_class_dist ayarına göre metin rengini seçer.
    """
    dist = style_cfg.get("contrast_class_dist", {"high": 0.7, "medium": 0.2, "low": 0.1})
    contrast_class = _pick_weighted(rng, dist)
    
    if contrast_class == "low":
        val = rng.randint(120, 170)  # Faks/soluk baskı hissi (Açık Gri)
    elif contrast_class == "medium":
        val = rng.randint(60, 119)   # Standart gri
    else:
        val = rng.randint(0, 59)     # Siyaha çok yakın (Yüksek kontrast)
        
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


def _font_supports_text(font: ImageFont.ImageFont, text: str) -> bool:
    """
    Tam kusursuz değil ama unsupported glyph / tofu riskini ciddi azaltır.
    """
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


def _choose_script_for_line(
    rng: random.Random,
    text_cfg: Dict[str, Any],
    line_kind: str = "text",
) -> str:
    dist = text_cfg.get("scripts_dist", {
        "latin": 0.45,
        "tr": 0.18,
        "de": 0.07,
        "ru": 0.10,
        "el": 0.06,
        "ar": 0.09,
        "symbols": 0.05,
    })

    if line_kind in {"title", "caption"}:
        dist = dict(dist)
        if "symbols" in dist:
            dist["symbols"] = min(float(dist["symbols"]), 0.02)

    return _pick_weighted(rng, dist)


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

    if candidates:
        tries = min(12, len(candidates))
        sampled = candidates[:] if len(candidates) <= tries else rng.sample(candidates, tries)

        for path in sampled:
            try:
                fnt = ImageFont.truetype(str(path), size=size)
                if _font_supports_text(fnt, probe_text):
                    return fnt
            except Exception:
                continue

    if script != "latin":
        latin_candidates = _font_candidates(fonts_dir, script="latin", role=role)
        tries = min(10, len(latin_candidates))
        sampled = latin_candidates[:] if len(latin_candidates) <= tries else rng.sample(latin_candidates, tries)

        for path in sampled:
            try:
                fnt = ImageFont.truetype(str(path), size=size)
                if _font_supports_text(fnt, _sample_probe_text_for_script("latin", role)):
                    return fnt
            except Exception:
                continue

    mono_candidates = _font_candidates(fonts_dir, script="latin", role="code")
    tries = min(8, len(mono_candidates))
    sampled = mono_candidates[:] if len(mono_candidates) <= tries else rng.sample(mono_candidates, tries)

    for path in sampled:
        try:
            fnt = ImageFont.truetype(str(path), size=size)
            return fnt
        except Exception:
            continue

    return ImageFont.load_default()


def _safe_font(fonts_dir: str | None, size: int, rng: random.Random) -> ImageFont.ImageFont:
    """
    Geriye dönük uyumluluk için.
    """
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


def _fit_rgba_contain(img_rgba: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    En-boy oranını koruyarak hedef kutuya sığdırır.
    Boş kalan alanlar transparan kalır.
    """
    target_w = max(1, int(target_w))
    target_h = max(1, int(target_h))

    src_w, src_h = img_rgba.size
    if src_w <= 0 or src_h <= 0:
        return Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))

    scale = min(target_w / src_w, target_h / src_h)
    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))

    resized = img_rgba.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    off_x = (target_w - new_w) // 2
    off_y = (target_h - new_h) // 2
    canvas.paste(resized, (off_x, off_y), resized)
    return canvas

def _rand_word_meaningful(rng: random.Random, script: str) -> str:
    if script == "tr":
        return rng.choice(_WORDS_TR)
    if script == "de":
        return rng.choice(_WORDS_DE)
    if script == "ru":
        return rng.choice(_WORDS_RU)
    if script == "el":
        return rng.choice(_WORDS_EL)
    if script == "ar":
        return rng.choice(_WORDS_AR)
    return rng.choice(_WORDS_LATIN)


def _rand_gibberish(rng: random.Random, script: str, n: int) -> str:
    if script == "latin":
        pool = _LATIN_CHARS + _DIGITS
        return "".join(rng.choice(pool) for _ in range(n))
    if script == "tr":
        pool = _LATIN_CHARS + _TR_EXTRA + _DIGITS
        return "".join(rng.choice(pool) for _ in range(n))
    if script == "de":
        pool = _LATIN_CHARS + _DE_EXTRA + _DIGITS
        return "".join(rng.choice(pool) for _ in range(n))
    if script == "ru":
        return _rand_from_range(rng, _CYR_START, _CYR_END, n)
    if script == "el":
        return _rand_from_range(rng, _GR_START, _GR_END, n)
    if script == "ar":
        return _rand_from_range(rng, _AR_START, _AR_END, n)
    if script == "symbols":
        pool = _SYMBOLS + _DIGITS
        return "".join(rng.choice(pool) for _ in range(n))
    pool = _LATIN_CHARS + _DIGITS
    return "".join(rng.choice(pool) for _ in range(n))


def _avg_char_px(draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont) -> float:
    probe = "MMMMMMMMMM"
    w = _measure_text(draw, probe, font)
    return max(3.0, float(w) / 10.0)


def _rand_code_token(rng: random.Random) -> str:
    head = rng.choice(["cfg", "data", "model", "train", "valid", "loss", "acc", "render", "mask", "bbox"])
    if rng.random() < 0.55:
        mid = rng.choice(["_", "__", ".", "::"])
        tail = rng.choice(["size", "w", "h", "dpi", "prob", "mean", "std", "seed", "id"])
        tok = f"{head}{mid}{tail}"
    else:
        tok = head

    if rng.random() < 0.35:
        tok += rng.choice(_CODE_OPS)
    if rng.random() < 0.25:
        tok += str(rng.randint(0, 999))
    if rng.random() < 0.25:
        tok = f"{tok}({rng.choice(['x', 'y', 'w', 'h', 'i', 'j'])})"
    return tok


def _make_line_text(
    rng: random.Random,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    max_width_px: int,
    *,
    density_mode: str,
    noise_level: str,
    text_cfg: Dict[str, Any],
    line_kind: str = "text",   # text | title | caption | table_cell | list | notes
    page_family: str = "report",
    forced_script: str | None = None,
) -> Tuple[str, str]:
    dist = text_cfg.get("scripts_dist", {
        "latin": 0.45,
        "tr": 0.18,
        "de": 0.07,
        "ru": 0.10,
        "el": 0.06,
        "ar": 0.09,
        "symbols": 0.05,
    })
    script = forced_script if forced_script is not None else _pick_weighted(rng, dist)

    style_dist = text_cfg.get("line_style_dist", {
        "prose": 0.54,
        "mixed": 0.18,
        "code": 0.10,
        "mathish": 0.07,
        "bars": 0.03,
        "noisy": 0.08,
    })

    if line_kind == "title":
        style_dist = {"prose": 0.78, "mixed": 0.14, "noisy": 0.08}
    elif line_kind == "caption":
        style_dist = {"prose": 0.82, "mixed": 0.10, "noisy": 0.08}
    elif line_kind == "table_cell":
        style_dist = {"prose": 0.55, "mixed": 0.20, "code": 0.15, "noisy": 0.10}
    elif line_kind == "list":
        style_dist = {"prose": 0.62, "mixed": 0.16, "code": 0.10, "noisy": 0.12}

    style = _pick_weighted(rng, style_dist)

    if line_kind == "title":
        fill_lo, fill_hi = 0.35, 0.72
    elif line_kind == "caption":
        fill_lo, fill_hi = 0.40, 0.85
    elif line_kind == "table_cell":
        fill_lo, fill_hi = 0.32, 0.92
    else:
        if density_mode == "ultra":
            fill_lo, fill_hi = 0.97, 1.00
        elif density_mode == "dense":
            fill_lo, fill_hi = 0.95, 0.99
        elif density_mode == "sparse":
            fill_lo, fill_hi = 0.60, 0.85
        elif density_mode == "mixed":
            fill_lo, fill_hi = 0.70, 0.95
        else:
            fill_lo, fill_hi = 0.92, 0.99

    if rng.random() < float(text_cfg.get("very_short_line_prob", 0.06)) and line_kind not in {"title", "caption"}:
        fill_lo, fill_hi = 0.30, 0.50
    if rng.random() < float(text_cfg.get("very_full_line_prob", 0.16)) and line_kind not in {"title"}:
        fill_lo, fill_hi = max(fill_lo, 0.93), 0.998

    fill_target = rng.uniform(fill_lo, fill_hi)

    punct_boost = 1.0
    if noise_level == "heavy":
        punct_boost = 1.7
    elif noise_level == "clean":
        punct_boost = 0.75

    p_mean = float(text_cfg.get("meaningful_prob", 0.68))
    p_gibb = float(text_cfg.get("gibberish_prob", 0.22))

    # YENİ: Bazen sayfada tamamen dillerin birbirine girdiği (Babel) satırlar olsun
    is_babel_mode = (rng.random() < 0.25) # %25 ihtimalle diller kelime kelime değişecek
    if is_babel_mode and line_kind not in {"title", "caption"}:
        code_switch_prob = rng.uniform(0.40, 0.85) # Çok yüksek ihtimalle her kelime farklı dil
    else:
        # Geri kalan %75 durumda kelimeler tek bir dile sadık kalacak (çok nadir araya başka dil sızar)
        code_switch_prob = float(text_cfg.get("code_switch_prob", 0.05 if style == "mixed" else 0.01))

    if line_kind == "title":
        p_mean = max(0.78, p_mean)
        p_gibb = min(0.10, p_gibb)

    elif line_kind == "caption":
        p_mean = max(0.74, p_mean)
        p_gibb = min(0.14, p_gibb)

    space_prof_dist = text_cfg.get(
        "space_profile_dist",
        {"tight": 0.95, "normal": 0.05, "loose": 0.00},
    )
    if density_mode in ("dense", "ultra"):
        space_prof_dist = dict(space_prof_dist)
        space_prof_dist["tight"] = float(space_prof_dist.get("tight", 0.88)) + 0.05

    if line_kind in {"title", "caption"}:
        space_prof_dist = {"tight": 0.55, "normal": 0.35, "loose": 0.10}

    space_profile = _pick_weighted(rng, space_prof_dist)
    base_tab_prob = float(text_cfg.get("tab_prob", 0.008))

    def pick_sep() -> str:
        if style == "bars":
            return ""

        tab_scale = 2.0 if space_profile == "loose" else (0.35 if space_profile == "tight" else 1.0)
        if rng.random() < base_tab_prob * tab_scale and line_kind not in {"title", "caption"}:
            return "\t"

        if space_profile == "tight":
            if density_mode in ("dense", "ultra"):
                return rng.choice(["", " ", " ", " ", " "])
            return rng.choice(["", " ", " ", " ", "  "])

        if space_profile == "loose":
            return rng.choice(["  ", "   ", "  ", " ", "   "])

        if density_mode == "sparse":
            return rng.choice([" ", "  ", "   "])

        return rng.choice(["", " ", " ", "  "])

    avg_px = _avg_char_px(draw, font)
    approx_chars = int((max_width_px * fill_target * 1.15) / avg_px)
    approx_chars = max(4, min(400, approx_chars))

    parts: List[str] = []
    cur_w = 0.0
    sep_cache: Dict[str, float] = {}

    def sep_w(s: str) -> float:
        if s not in sep_cache:
            sep_cache[s] = _measure_text(draw, s, font) if s else 0.0
        return sep_cache[s]

    def tok_w(s: str) -> float:
        return _measure_text(draw, s, font)

    def pick_script_for_token(primary: str) -> str:
        # YENİ: forced_script verilmiş olsa bile, eğer "Babel" (karışık) moddaysak 
        # (yani code_switch_prob tutarsa) dili o kelime için değiştirmesine izin ver!
        if rng.random() < code_switch_prob and line_kind not in {"title"}:
            alt = {k: v for k, v in dist.items() if k != primary}
            if alt:
                return _pick_weighted(rng, alt)
        return primary

    def make_token() -> str:
        tok_script = pick_script_for_token(script)

        if style == "bars":
            run = rng.randint(8, max(10, min(160, approx_chars)))
            ch = rng.choice(_BAR_CHARS)
            if rng.random() < 0.10:
                return ch * rng.randint(6, 20) + " " + _rand_word_meaningful(rng, tok_script)
            return ch * run

        if style == "code":
            if rng.random() < 0.72:
                tok = _rand_code_token(rng)
            else:
                tok = _rand_gibberish(rng, "latin", rng.randint(2, 12))
            if rng.random() < 0.15:
                tok += rng.choice([";", ",", ":", ".", "()"])
            return tok

        if style == "mathish":
            if rng.random() < 0.58:
                tok = _rand_gibberish(rng, "symbols", rng.randint(6, 28))
            elif rng.random() < 0.28:
                tok = (
                    rng.choice(["(", "[", "{"])
                    + _rand_gibberish(rng, "symbols", rng.randint(3, 12))
                    + rng.choice([")", "]", "}"])
                )
            else:
                tok = _rand_word_meaningful(rng, tok_script)
            return tok

        r = rng.random()
        if r < p_mean:
            tok = _rand_word_meaningful(rng, tok_script)
        elif r < p_mean + p_gibb:
            tok = _rand_gibberish(rng, tok_script, rng.randint(2, 12))
        else:
            base = _rand_word_meaningful(rng, tok_script)
            suffix = _rand_gibberish(
                rng,
                "symbols" if rng.random() < 0.45 else tok_script,
                rng.randint(1, 6),
            )
            tok = base + suffix

        if rng.random() < 0.05 and density_mode in ("sparse", "normal", "mixed") and line_kind not in {"title", "caption"}:
            tok = rng.choice(_BULLETS) + " " + tok

        if rng.random() < 0.20 * punct_boost:
            tok += rng.choice(list(_PUNCT))

        if style == "noisy" and rng.random() < 0.22 * punct_boost:
            tok += rng.choice(_CODE_OPS)

        if rng.random() < 0.05:
            tok = tok.upper()

        return tok

    target_tokens = max(10, min(300, int(approx_chars / rng.uniform(2.5, 5.0))))
    if density_mode == "sparse":
        target_tokens = max(4, min(target_tokens, rng.randint(8, 20)))
    elif density_mode == "ultra":
        target_tokens = max(target_tokens, rng.randint(60, 200))

    if line_kind == "title":
        target_tokens = max(2, min(target_tokens, rng.randint(2, 9)))
    elif line_kind == "caption":
        target_tokens = max(3, min(target_tokens, rng.randint(4, 16)))
    elif line_kind == "table_cell":
        target_tokens = max(1, min(target_tokens, rng.randint(1, 8)))

    for _ in range(target_tokens):
        tok = make_token()
        if not tok:
            continue

        sep = "" if not parts else pick_sep()
        w_add = sep_w(sep) + tok_w(tok)

        if cur_w + w_add > max_width_px:
            if style == "bars" and len(tok) > 8:
                remaining = max(0.0, float(max_width_px) - cur_w - sep_w(sep))
                if remaining > 3:
                    keep = max(3, int(remaining / max(3.0, avg_px)))
                    tok2 = tok[:keep]
                    if tok_w(tok2) <= remaining:
                        parts.append(sep + tok2)
                        cur_w += sep_w(sep) + tok_w(tok2)
            break

        parts.append(sep + tok)
        cur_w += w_add

        if density_mode in ("dense", "ultra") and line_kind not in {"title", "caption"} and rng.random() < 0.03:
            break

    text = "".join(parts).strip()
    if not text:
        text = _rand_word_meaningful(rng, script)

    for _ in range(8):
        if _measure_text(draw, text, font) <= max_width_px:
            break
        text = text[: max(1, int(len(text) * 0.94))].rstrip()

    if max_width_px <= 30:
        return text[: max(1, len(text) // 2)], script

    return text, script


# -------------------------
# Geometry helpers
# -------------------------

def _clamp_box(x0: int, y0: int, x1: int, y1: int, w: int, h: int) -> Tuple[int, int, int, int]:
    x0 = max(0, min(w - 1, x0))
    y0 = max(0, min(h - 1, y0))
    x1 = max(0, min(w, x1))
    y1 = max(0, min(h, y1))
    if x1 <= x0:
        x1 = min(w, x0 + 1)
    if y1 <= y0:
        y1 = min(h, y0 + 1)
    return x0, y0, x1, y1


def _intersects(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def _pad_box(b: Tuple[int, int, int, int], pad: int, w: int, h: int) -> Tuple[int, int, int, int]:
    x0, y0, x1, y1 = b
    return _clamp_box(x0 - pad, y0 - pad, x1 + pad, y1 + pad, w, h)


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


def _make_random_figure_patch(rng: random.Random, ww: int, hh: int, family: str) -> Image.Image:
    seed_np = rng.randint(0, 2**32 - 1)
    np_rng = np.random.default_rng(seed_np)

    ww = max(1, int(ww))
    hh = max(1, int(hh))

    # Çok küçük patch'lerde güvenli fallback
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

        # X ve Y margin ayrı hesaplanır
        margin_x = max(8, ww // 12)
        margin_y = max(8, hh // 12)

        # İç alanı garanti altına al
        margin_x = min(margin_x, max(1, (ww - 12) // 2))
        margin_y = min(margin_y, max(1, (hh - 12) // 2))

        x_min = margin_x
        x_max = ww - margin_x
        y_min = margin_y + 5
        y_max = hh - margin_y - 5

        # Eğer chart için yeterli alan yoksa basit fallback chart çiz
        if x_min >= x_max or y_min > y_max or (ww < 40) or (hh < 30):
            # küçük alanda sade bir mini chart
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
                    d.line((pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]), fill=(30, 30, 30), width=1)

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

def _jump_past_obstacle(
    lbox: Tuple[int, int, int, int],
    obstacles: List[Tuple[int, int, int, int]],
    ycur: int,
    *,
    gap: int = 2,
) -> int:
    hit_y1 = None
    for ob in obstacles:
        if _intersects(lbox, ob):
            hit_y1 = max(hit_y1 or 0, ob[3])
    if hit_y1 is None:
        return ycur
    return max(ycur + 1, int(hit_y1 + gap))


def _try_relocate_line_bbox_down(
    x: int,
    y: int,
    ww: int,
    hh: int,
    obstacles: List[Tuple[int, int, int, int]],
    *,
    w: int,
    h: int,
    y_max: int,
    tries: int = 10,
    gap: int = 15,
) -> Tuple[bool, Tuple[int, int, int, int]]:
    ycur = int(y)
    for _ in range(tries):
        lbox = (x, ycur, x + ww, ycur + hh)
        if not any(_intersects(lbox, ob) for ob in obstacles):
            return True, (x, ycur, ww, hh)

        y_next = _jump_past_obstacle(lbox, obstacles, ycur, gap=gap)
        if y_next == ycur:
            y_next += gap

        if y_next + hh > y_max:
            break

        ycur = int(y_next)

    return False, (x, y, ww, hh)


def _line_kind_from_block(block_type: str) -> str:
    if block_type == "title":
        return "title"
    if block_type == "caption":
        return "caption"
    if block_type == "table":
        return "table_cell"
    if block_type == "list":
        return "list"
    return "text"


def _collect_block_line_map(page_spec: PageSpec) -> Dict[int, List[Any]]:
    out: Dict[int, List[Any]] = {}
    for ln in page_spec.lines:
        out.setdefault(int(ln.block_id), []).append(ln)
    for bid in out:
        out[bid].sort(key=lambda z: (int(z.line_order_in_block), int(z.global_line_order)))
    return out

def _draw_table_structure(
    draw: ImageDraw.ImageDraw,
    bx0: int,
    by0: int,
    bx1: int,
    by1: int,
    *,
    rows: int,
    cols: int,
    style: Dict[str, Any],
    rng: random.Random,
) -> None:
    rows = max(1, int(rows))
    cols = max(1, int(cols))

    bw = max(1, bx1 - bx0)
    bh = max(1, by1 - by0)

    cell_w = max(1, bw // cols)
    cell_h = max(1, bh // rows)

    header_rows = max(0, int(style.get("header_rows", 0)))
    header_cols = max(0, int(style.get("header_cols", 0)))
    border_mode = str(style.get("border_mode", "full_grid"))
    zebra_rows = bool(style.get("zebra_rows", False))
    light_rules = bool(style.get("light_rules", False))

    rule_dark = 70 if not light_rules else 110
    rule_mid = 95 if not light_rules else 140
    rule_light = 180 if not light_rules else 205

    outer_col = (rule_dark, rule_dark, rule_dark)
    major_col = (rule_mid, rule_mid, rule_mid)
    minor_col = (rule_light, rule_light, rule_light)

    # header fill
    if header_rows > 0:
        for r in range(min(header_rows, rows)):
            y0 = by0 + r * cell_h
            y1 = by0 + min(bh, (r + 1) * cell_h)
            draw.rectangle((bx0, y0, bx1, y1), fill=(242, 242, 242))

    if header_cols > 0:
        for c in range(min(header_cols, cols)):
            x0 = bx0 + c * cell_w
            x1 = bx0 + min(bw, (c + 1) * cell_w)
            draw.rectangle((x0, by0, x1, by1), fill=(246, 246, 246))

    # zebra rows
    if zebra_rows and rows >= 3:
        start_r = max(1, header_rows)
        for r in range(start_r, rows):
            if (r - start_r) % 2 == 1:
                y0 = by0 + r * cell_h
                y1 = by0 + min(bh, (r + 1) * cell_h)
                draw.rectangle((bx0, y0, bx1, y1), fill=(248, 248, 248))

    # border styles
    if border_mode == "borderless":
        if header_rows > 0:
            y = by0 + header_rows * cell_h
            draw.line((bx0, y, bx1, y), fill=major_col, width=2)
        return

    if border_mode == "outer_only":
        draw.rectangle((bx0, by0, bx1, by1), outline=outer_col, width=2)
        return

    if border_mode == "header_rule":
        if header_rows > 0:
            y = by0 + header_rows * cell_h
            draw.line((bx0, y, bx1, y), fill=outer_col, width=2)
        draw.line((bx0, by0, bx1, by0), fill=major_col, width=1)
        draw.line((bx0, by1, bx1, by1), fill=major_col, width=1)
        return

    if border_mode == "rows_only":
        for r in range(1, rows):
            y = by0 + (bh * r) // rows
            col = outer_col if header_rows > 0 and r == header_rows else minor_col
            width = 2 if header_rows > 0 and r == header_rows else 1
            draw.line((bx0, y, bx1, y), fill=col, width=width)
        return

    if border_mode == "cols_only":
        for c in range(1, cols):
            x = bx0 + (bw * c) // cols
            col = outer_col if header_cols > 0 and c == header_cols else minor_col
            width = 2 if header_cols > 0 and c == header_cols else 1
            draw.line((x, by0, x, by1), fill=col, width=width)
        return

    if border_mode == "ledger":
        draw.line((bx0, by0, bx1, by0), fill=outer_col, width=2)
        if header_rows > 0:
            y = by0 + header_rows * cell_h
            draw.line((bx0, y, bx1, y), fill=outer_col, width=2)
        for r in range(max(1, header_rows + 1), rows):
            y = by0 + (bh * r) // rows
            draw.line((bx0, y, bx1, y), fill=minor_col, width=1)
        draw.line((bx0, by1, bx1, by1), fill=major_col, width=1)
        return

    # default: full_grid
    draw.rectangle((bx0, by0, bx1, by1), outline=outer_col, width=2)

    for c in range(1, cols):
        x = bx0 + (bw * c) // cols
        col = outer_col if header_cols > 0 and c == header_cols else major_col
        width = 2 if header_cols > 0 and c == header_cols else 1
        draw.line((x, by0, x, by1), fill=col, width=width)

    for r in range(1, rows):
        y = by0 + (bh * r) // rows
        col = outer_col if header_rows > 0 and r == header_rows else major_col
        width = 2 if header_rows > 0 and r == header_rows else 1
        draw.line((bx0, y, bx1, y), fill=col, width=width)


# -------------------------
# Renderer
# -------------------------

def render_page_layers(page_spec: PageSpec, cfg: Any, rng: random.Random) -> Dict[str, Any]:
    page_cfg = (cfg.raw.get("page", {}) or {}) if hasattr(cfg, "raw") else {}
    render_cfg = cfg.render()
    text_cfg = render_cfg.get("text", {}) or {}
    non_text_cfg = render_cfg.get("non_text", {}) or {}
    style_cfg = (cfg.raw.get("style", {}) or {}) if hasattr(cfg, "raw") else {}

    w, h = int(page_spec.w), int(page_spec.h)
    bg = tuple(int(x) for x in page_cfg.get("bg_color_rgb", [255, 255, 255]))

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    mask_text = Image.new("L", (w, h), 0)
    mask_math = Image.new("L", (w, h), 0)
    mdraw_t = ImageDraw.Draw(mask_text)
    mdraw_m = ImageDraw.Draw(mask_math)

    fonts_dir = text_cfg.get("fonts_dir", None)

    if bool(non_text_cfg.get("enable", True)) and rng.random() < float(non_text_cfg.get("watermark_prob", 0.06)):
        for k in range(0, w, max(220, w // 12)):
            draw.line((k, 0, k + h, h), fill=(240, 240, 240), width=3)

    actual_has_table = False
    actual_has_figure = False
    actual_has_equation = False

    book_cfg = text_cfg.get("book_mode", {}) or {}
    book_enable = bool(book_cfg.get("enable", True)) and page_spec.page_family == "book"

    dpi = int(page_spec.dpi)
    base_pt = int(book_cfg.get("base_font_pt", 11))
    base_size = int(base_pt * (dpi / 300.0))
    base_size = max(10, min(18, base_size))

    mleft = float(book_cfg.get("margin_left", 0.10))
    mright = float(book_cfg.get("margin_right", 0.08))
    mtop = float(book_cfg.get("margin_top", 0.06))
    mbot = float(book_cfg.get("margin_bottom", 0.08))
    gutter_ratio = float(book_cfg.get("gutter_ratio", 0.06))

    xL = int(w * mleft)
    xR = int(w * (1.0 - mright))
    yT = int(h * mtop)
    yB = int(h * (1.0 - mbot))
    _body_region = (xL, yT, xR, yB)

    hard_obstacles: List[Tuple[int, int, int, int]] = []

    gt_line_text: Dict[int, str] = {}
    gt_line_script: Dict[int, str] = {}
    gt_line_latex: Dict[int, str] = {}
    gt_script_hist: Dict[str, int] = {}

    extra_blocks: List[Dict[str, Any]] = []
    extra_lines: List[Dict[str, Any]] = []

    max_block_id = max([b.block_id for b in page_spec.blocks], default=-1)
    max_line_id = max([ln.line_id for ln in page_spec.lines], default=-1)
    max_glo = max([ln.global_line_order for ln in page_spec.lines], default=-1)
    next_block_id = max_block_id + 1
    next_line_id = max_line_id + 1
    next_glo = max_glo + 1

    probe_size = int(max(14, min(80, int(base_size * 4.0))))
    probe_font = _safe_font_for_text(
        fonts_dir,
        size=probe_size,
        rng=rng,
        script="latin",
        role="body",
        probe_text="example data line",
    )
    word_gap_px = int(round(_measure_text(draw, "   ", probe_font)))
    word_gap_px = max(4, word_gap_px)
    jump_gap_px = max(15, int(word_gap_px) + 4)

    local_scale_prob = float(style_cfg.get("local_scale_mode_prob", 0.45))
    enforce_local = (page_spec.scale_profile == "hires_crop")

    latex_cfg = render_cfg.get("latex", {}) or {}
    latex_enable = bool(latex_cfg.get("enable", True))
    pdflatex_cmd = latex_cfg.get("compiler", "pdflatex")
    timeout_s = int(latex_cfg.get("timeout_s", 12))
    raster_dpi = int(latex_cfg.get("raster_dpi", 300))

    relocated_bbox_by_line_id: Dict[int, Tuple[int, int, int, int]] = {}
    block_line_map = _collect_block_line_map(page_spec)

    # --------------------------------------------------
    # PASS 1: Block-aware render
    # --------------------------------------------------
    for b in sorted(page_spec.blocks, key=lambda z: int(z.block_order)):
        bx, by, bw, bh = map(int, b.bbox)
        block_box = _clamp_box(bx, by, bx + bw, by + bh, w, h)
        bx0, by0, bx1, by1 = block_box
        bw = max(1, bx1 - bx0)
        bh = max(1, by1 - by0)

        line_objs = block_line_map.get(int(b.block_id), [])
        btype = str(b.block_type)

        if btype == "figure":
            actual_has_figure = True
            fig_family = rng.choice(["photo", "chart", "diagram", "texture"])
            patch = _make_random_figure_patch(rng, bw, bh, fig_family)
            img.paste(patch, (bx0, by0))
            draw.rectangle((bx0, by0, bx1, by1), outline=(40, 40, 40), width=2)
            hard_obstacles.append(_pad_box((bx0, by0, bx1, by1), 8, w, h))
            continue

        if btype == "table":
            actual_has_table = True

            rows = int(b.style.get("table_rows", 0) or 0)
            cols = int(b.style.get("table_cols", 0) or 0)

            if rows <= 0 or cols <= 0:
                cell_lines = [ln for ln in line_objs if str(ln.line_type) == "table_cell"]
                n_cells = max(4, len(cell_lines))
                cols = max(2, min(6, int(round(n_cells ** 0.5))))
                rows = max(2, int(np.ceil(n_cells / cols)))

            _draw_table_structure(
                draw,
                bx0,
                by0,
                bx1,
                by1,
                rows=rows,
                cols=cols,
                style=b.style,
                rng=rng,
            )

            hard_obstacles.append(_pad_box((bx0, by0, bx1, by1), 8, w, h))
            continue

    # --------------------------------------------------
    # PASS 2: Line render using PageSpec
    # --------------------------------------------------
    for ln in page_spec.lines:
        x, y, ww, hh = ln.bbox
        if ww <= 6 or hh <= 8:
            continue

        x0, y0, x1, y1 = _clamp_box(int(x), int(y), int(x + ww), int(y + hh), w, h)
        x = x0
        y = y0
        ww = max(1, x1 - x0)
        hh = max(1, y1 - y0)

        block_obj = next((b for b in page_spec.blocks if int(b.block_id) == int(ln.block_id)), None)
        block_type = str(block_obj.block_type) if block_obj is not None else "paragraph"
        line_kind = _line_kind_from_block(block_type)

        if block_type == "figure":
            continue

        if ln.line_type == "table_cell":
            ok = True
        else:
            ok, (x, y, ww, hh) = _try_relocate_line_bbox_down(
                x, y, ww, hh,
                hard_obstacles,
                w=w, h=h, y_max=yB,
                tries=10,
                gap=jump_gap_px,
            )
            if not ok:
                continue

        relocated_bbox_by_line_id[int(ln.line_id)] = (int(x), int(y), int(ww), int(hh))
        lbox = (x, y, x + ww, y + hh)

        if ln.line_type == "math":
            actual_has_equation = True
            expr = sample_latex_expr(rng, level=page_spec.noise_level)
            gt_line_latex[ln.line_id] = expr
            gt_script_hist["math"] = gt_script_hist.get("math", 0) + 1

            if latex_enable:
                try:
                    eq = render_latex_to_rgba(
                        expr,
                        pdflatex_cmd=pdflatex_cmd,
                        timeout_s=timeout_s,
                        raster_dpi=raster_dpi,
                    ).convert("RGBA")

                    eq = _fit_rgba_contain(eq, max(10, ww), max(10, hh))

                    img.paste(eq, (x, y), eq)
                    _paste_alpha_as_binary(mask_math, eq.split()[-1], x, y)
                except LatexRenderError:
                    fnt = _fit_font_to_bbox_height(
                        fonts_dir,
                        desired_size=base_size,
                        bbox_h=hh,
                        rng=rng,
                        script="symbols",
                        role="body",
                        probe_text="∑ √ ≤ ≥",
                    )
                    math_color = _sample_contrast_color(rng, style_cfg)
                    _draw_text_glyph_mask(draw, mdraw_m, x, y, "math", fnt, math_color)
            
            else:
                fnt = _fit_font_to_bbox_height(
                    fonts_dir,
                    desired_size=base_size,
                    bbox_h=hh,
                    rng=rng,
                    script="symbols",
                    role="body",
                    probe_text="∑ √ ≤ ≥",
                )
                math_color = _sample_contrast_color(rng, style_cfg)
                _draw_text_glyph_mask(draw, mdraw_m, x, y, "math", fnt, math_color)

            hard_obstacles.append(_pad_box(lbox, 5, w, h))
            continue

        # YENİ MANTIK: Kutu yüksekliğine (hh) dinamik olarak oturt.
        # Bu sayede 2-48 punto arası devasa boyutlara çıkabilmesine izin veriyoruz.
        if block_type == "title":
            desired = int(hh * rng.uniform(0.70, 0.85))
        elif block_type == "caption":
            desired = int(hh * rng.uniform(0.60, 0.75))
        elif block_type == "table":
            desired = int(hh * rng.uniform(0.55, 0.70))
        elif block_type == "list":
            desired = int(hh * rng.uniform(0.65, 0.80))
        else:
            desired = int(hh * rng.uniform(0.65, 0.80))

        if enforce_local or (rng.random() < local_scale_prob):
            desired += rng.randint(-2, 4)

        # Üst limiti (eski 24 px sınırı) kaldırdık, artık alt sınır hariç özgür
        desired = max(8, desired)

        density_mode = page_spec.density_level
        if block_type == "title":
            density_mode = "normal"
        elif block_type == "caption":
            density_mode = "normal"

        script = _choose_script_for_line(rng, text_cfg, line_kind=line_kind)

        role = "body"
        if block_type == "title":
            role = "title"
        elif block_type == "caption":
            role = "caption"
        elif block_type == "table":
            role = "table"
        elif line_kind == "list":
            role = "body"

        fnt = _fit_font_to_bbox_height(
            fonts_dir,
            desired_size=desired,
            bbox_h=hh,
            rng=rng,
            script=script,
            role=role,
            probe_text=_sample_probe_text_for_script(script, role),
        )

        s, script = _make_line_text(
            rng,
            draw,
            fnt,
            max_width_px=max(10, ww - 4),
            density_mode=density_mode,
            noise_level=page_spec.noise_level,
            text_cfg=text_cfg,
            line_kind=line_kind,
            page_family=page_spec.page_family,
            forced_script=script,
        )

        text_color = _sample_contrast_color(rng, style_cfg) # Rengi örnekle
        _draw_text_glyph_mask(draw, mdraw_t, x, y, s, fnt, text_color) # Rengi kullan


        gt_line_text[ln.line_id] = s
        gt_line_script[ln.line_id] = script
        gt_script_hist[script] = gt_script_hist.get(script, 0) + 1

        hard_obstacles.append(_pad_box(lbox, 5, w, h))

    # --------------------------------------------------
    # PASS 3: Conservative filler only for sparse book pages
    # --------------------------------------------------
    if book_enable:
        existing_text_lines = sum(1 for _ln in page_spec.lines if str(_ln.line_type) != "math")
        if existing_text_lines < 8:
            base_font_size = base_size
            line_spacing = float(book_cfg.get("line_spacing", 1.15))
            indent_ratio = float(book_cfg.get("paragraph_indent_ratio", 0.035))
            para_gap_mult = float(book_cfg.get("paragraph_gap_mult", 0.35))

            cols_body = 1
            if page_spec.layout_type == "double_col" and page_spec.density_level == "dense":
                dense_two_columns = bool(book_cfg.get("dense_two_columns", True))
                if dense_two_columns:
                    cols_body = 2

            gutter = int((xR - xL) * gutter_ratio) if cols_body == 2 else 0
            if cols_body == 2:
                gutter = max(gutter, int(word_gap_px) + 2)

            col_w = (xR - xL - gutter) // cols_body
            next_block_id_local = next_block_id
            next_line_id_local = next_line_id
            next_glo_local = next_glo

            for c in range(cols_body):
                cx0 = xL + c * (col_w + gutter)
                cx1 = cx0 + col_w

                seg_y0 = yT
                seg_y1 = yB
                if seg_y1 - seg_y0 < 140:
                    continue

                block_id = next_block_id_local
                next_block_id_local += 1
                extra_blocks.append({
                    "block_id": block_id,
                    "block_type": "auto_paragraph_block",
                    "block_order": len(extra_blocks),
                    "column_id": c,
                    "bbox": [cx0, seg_y0, cx1 - cx0, seg_y1 - seg_y0],
                    "style": {
                        "book_mode": True,
                        "filler": True,
                    },
                })

                jitter = rng.randint(-2, 6)
                desired_size = max(9, min(26, base_font_size + jitter))
                filler_script = _choose_script_for_line(rng, text_cfg, line_kind="text")
                base_font = _safe_font_for_text(
                    fonts_dir,
                    size=desired_size,
                    rng=rng,
                    script=filler_script,
                    role="body",
                    probe_text=_sample_probe_text_for_script(filler_script, "body"),
                )

                fh = _font_height_px(base_font)
                lh = max(fh + 3, int(round(fh * line_spacing)))

                ycur = seg_y0
                in_block = 0
                added_here = 0

                while ycur + lh <= seg_y1 and added_here < 18:
                    para_len = rng.randint(3, 6)
                    indent_px = int((cx1 - cx0) * indent_ratio)

                    for li in range(para_len):
                        if ycur + lh > seg_y1 or added_here >= 18:
                            break

                        lbox = (cx0, ycur, cx1, ycur + lh)

                        if any(_intersects(lbox, ob) for ob in hard_obstacles):
                            ycur = _jump_past_obstacle(lbox, hard_obstacles, ycur, gap=jump_gap_px)
                            if ycur + lh > seg_y1:
                                break
                            continue

                        rag = rng.uniform(0.50, 0.85) if li == para_len - 1 else rng.uniform(0.95, 1.00)
                        maxw = int((cx1 - cx0 - 8) * rag)
                        x_text = cx0 + (indent_px if li == 0 else 0)

                        script = _choose_script_for_line(rng, text_cfg, line_kind="text")
                        fnt = _fit_font_to_bbox_height(
                            fonts_dir,
                            desired_size=desired_size,
                            bbox_h=lh,
                            rng=rng,
                            script=script,
                            role="body",
                            probe_text=_sample_probe_text_for_script(script, "body"),
                        )
                        s, script = _make_line_text(
                            rng,
                            draw,
                            fnt,
                            max_width_px=max(10, maxw - (indent_px if li == 0 else 0)),
                            density_mode=page_spec.density_level,
                            noise_level=page_spec.noise_level,
                            text_cfg=text_cfg,
                            line_kind="text",
                            page_family=page_spec.page_family,
                            forced_script=script,
                        )

                        filler_color = _sample_contrast_color(rng, style_cfg)
                        _draw_text_glyph_mask(draw, mdraw_t, x_text, ycur, s, fnt, filler_color)
                                                
                        lid = next_line_id_local
                        next_line_id_local += 1
                        extra_lines.append({
                            "line_id": lid,
                            "block_id": block_id,
                            "line_type": "text",
                            "line_order_in_block": in_block,
                            "global_line_order": next_glo_local,
                            "bbox": [x_text, ycur, max(10, cx1 - x_text), lh],
                            "quad": None,
                            "is_hard": False,
                        })
                        next_glo_local += 1
                        in_block += 1
                        added_here += 1

                        gt_line_text[lid] = s
                        gt_line_script[lid] = script
                        gt_script_hist[script] = gt_script_hist.get(script, 0) + 1

                        hard_obstacles.append(_pad_box((x_text, ycur, x_text + max(10, cx1 - x_text), ycur + lh), 4, w, h))
                        ycur += lh

                    ycur += int(lh * para_gap_mult)

            next_block_id = next_block_id_local
            next_line_id = next_line_id_local
            next_glo = next_glo_local

    # -------------------------
    # Export arrays
    # -------------------------
    image_u8 = np.array(img, dtype=np.uint8)
    mask_text_u8 = np.array(mask_text, dtype=np.uint8)
    mask_math_u8 = np.array(mask_math, dtype=np.uint8)

    mask_text_u8 = np.where(mask_text_u8 > 0, 255, 0).astype(np.uint8)
    mask_math_u8 = np.where(mask_math_u8 > 0, 255, 0).astype(np.uint8)

    # -------------------------
    # Annotation
    # -------------------------
    lines_base: List[Dict[str, Any]] = []
    for ln in page_spec.lines:
        bb = relocated_bbox_by_line_id.get(int(ln.line_id), tuple(ln.bbox))
        lines_base.append({
            "line_id": ln.line_id,
            "block_id": ln.block_id,
            "line_type": ln.line_type,
            "line_order_in_block": ln.line_order_in_block,
            "global_line_order": ln.global_line_order,
            "bbox": list(bb),
            "quad": ln.quad,
            "is_hard": bool(ln.is_hard),
        })

    ann = {
        "version": "ai1-ds-v1.3.2",
        "page_id": page_spec.page_id,
        "size": {"w": w, "h": h, "dpi": page_spec.dpi},
        "meta": {
            "page_family": getattr(page_spec, "page_family", "report"),
            "layout_type": page_spec.layout_type,
            "noise_level": page_spec.noise_level,
            "density_level": page_spec.density_level,
            "scale_profile": page_spec.scale_profile,
            "has_table": bool(actual_has_table),
            "has_equation": bool(actual_has_equation),
            "has_figure": bool(actual_has_figure),
            "rotation_deg": page_spec.rotation_deg,
            "perspective": bool(page_spec.perspective),
            "book_mode": bool(book_enable),
        },
        "blocks": [
            {
                "block_id": b.block_id,
                "block_type": b.block_type,
                "block_order": b.block_order,
                "column_id": b.column_id,
                "bbox": list(b.bbox),
                "style": b.style,
            }
            for b in page_spec.blocks
        ] + extra_blocks,
        "lines": lines_base + extra_lines,
    }

    for item in ann["lines"]:
        lid = int(item["line_id"])
        if item["line_type"] == "math":
            if lid in gt_line_latex:
                item["gt_latex"] = gt_line_latex[lid]
        else:
            if lid in gt_line_text:
                item["gt_text"] = gt_line_text[lid]
                item["gt_script"] = gt_line_script.get(lid, "unknown")

    ordered = sorted(
        [(int(ln["global_line_order"]), ln.get("gt_text", "")) for ln in ann["lines"] if "gt_text" in ln],
        key=lambda x: int(x[0]),
    )
    ann["gt_page_text"] = "\n".join(t for _, t in ordered).strip()

    ann["gt_stats"] = {
        "scripts_hist": gt_script_hist,
        "has_gt_text_lines": sum(1 for ln in ann["lines"] if "gt_text" in ln),
        "has_gt_math_lines": sum(1 for ln in ann["lines"] if "gt_latex" in ln),
        "book_mode_added_lines": int(len(extra_lines)),
    }

    return {
        "image_u8": image_u8,
        "mask_text_u8": mask_text_u8,
        "mask_math_u8": mask_math_u8,
        "ann": ann,
    }