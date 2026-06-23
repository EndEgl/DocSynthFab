# src/docsynthfab/render/text_synth.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from PIL import ImageDraw, ImageFont

from docsynthfab.content import TextProvider

from .draw_utils import _measure_text, _pick_weighted


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

_BAR_CHARS = "█▓▒░▮▰▱▁▂▃▄▅▆▇─━═—–·•▪▫"
_CODE_OPS = ["==", "!=", "<=", ">=", "->", "::", "=>", "&&", "||", "+=", "-=", "*=", "/="]
_BULLETS = ["•", "-", "–", "—", "◦", "▪", "→"]


def _rand_from_range(rng: random.Random, a: int, b: int, k: int) -> str:
    return "".join(chr(rng.randint(a, b)) for _ in range(k))


def _content_pure_mode_from_cfg(content_cfg: Dict[str, Any]) -> str:
    """
    Return pure content mode based on content.block_mix.

    Possible values:
    - table_only
    - latex_only
    - text_only
    - mixed
    """
    block_mix = content_cfg.get("block_mix", {}) or {}

    if not isinstance(block_mix, dict):
        return "mixed"

    def _read(name: str) -> float:
        try:
            return max(0.0, float(block_mix.get(name, 0.0)))
        except Exception:
            return 0.0

    text = _read("text")
    table = _read("table")
    latex = _read("latex")

    total = text + table + latex

    if total <= 0.0:
        return "mixed"

    text_p = text / total
    table_p = table / total
    latex_p = latex / total

    if table_p >= 0.999 and text_p <= 0.001 and latex_p <= 0.001:
        return "table_only"

    if latex_p >= 0.999 and text_p <= 0.001 and table_p <= 0.001:
        return "latex_only"

    if text_p >= 0.999 and table_p <= 0.001 and latex_p <= 0.001:
        return "text_only"

    return "mixed"


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
    head = rng.choice([
        "cfg", "data", "model", "train", "valid",
        "loss", "acc", "render", "mask", "bbox",
    ])

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


def _provider_token_or_empty(
    text_provider: TextProvider | None,
    *,
    line_kind: str,
    style: str,
) -> str:
    if text_provider is None:
        return ""

    if style in {"bars", "code", "mathish"}:
        return ""

    provider_line_kind = "paragraph"

    if line_kind == "table_cell":
        provider_line_kind = "table_cell"
    elif line_kind in {"title", "caption", "list"}:
        provider_line_kind = "text"
    elif line_kind in {"text", "paragraph"}:
        provider_line_kind = "paragraph"

    txt = text_provider.next_text(line_type=provider_line_kind).strip()
    return txt


def _fit_provider_text_to_width(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    text: str,
    max_width_px: int,
    *,
    min_words: int = 4,
) -> str:
    """
    Fit provider text to one rendered line by keeping whole words.
    Avoid returning one-token paragraph lines.
    """
    words = [w for w in str(text or "").split() if w]

    if not words:
        return ""

    kept: List[str] = []

    for word in words:
        candidate = " ".join(kept + [word])

        if _measure_text(draw, candidate, font) <= max_width_px:
            kept.append(word)
        else:
            break

    if len(kept) >= int(min_words):
        return " ".join(kept).strip()

    return ""


def _make_line_text(
    rng: random.Random,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    max_width_px: int,
    *,
    density_mode: str,
    noise_level: str,
    text_cfg: Dict[str, Any],
    text_provider: TextProvider | None = None,
    line_kind: str = "text",
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

    global_style_dist = text_cfg.get("line_style_dist", {
        "prose": 0.54,
        "mixed": 0.18,
        "code": 0.10,
        "mathish": 0.07,
        "bars": 0.03,
        "noisy": 0.08,
    })

    style_dist = dict(global_style_dist) if isinstance(global_style_dist, dict) else {
        "prose": 0.54,
        "mixed": 0.18,
        "code": 0.10,
        "mathish": 0.07,
        "bars": 0.03,
        "noisy": 0.08,
    }

    if line_kind == "title":
        style_dist = {"prose": 0.78, "mixed": 0.14, "code": 0.0, "mathish": 0.0, "bars": 0.0, "noisy": 0.02}
    elif line_kind == "caption":
        style_dist = {"prose": 0.82, "mixed": 0.10, "code": 0.0, "mathish": 0.0, "bars": 0.0, "noisy": 0.02}
    elif line_kind == "table_cell":
        style_dist = {"prose": 0.82, "mixed": 0.18, "code": 0.0, "mathish": 0.0, "bars": 0.0, "noisy": 0.0}
    elif line_kind == "list":
        style_dist = {"prose": 0.82, "mixed": 0.18, "code": 0.0, "mathish": 0.0, "bars": 0.0, "noisy": 0.0}

    if isinstance(global_style_dist, dict):
        for key in ("code", "mathish", "bars", "noisy"):
            global_value = float(global_style_dist.get(key, 0.0) or 0.0)
            local_value = float(style_dist.get(key, 0.0) or 0.0)
            style_dist[key] = min(local_value, global_value)

    global_style_dist = text_cfg.get("line_style_dist", {})

    if isinstance(global_style_dist, dict):
        if float(global_style_dist.get("code", 1.0) or 0.0) <= 0.0:
            style_dist["code"] = 0.0
            style_dist["mathish"] = 0.0
            style_dist["bars"] = 0.0

        if float(global_style_dist.get("noisy", 1.0) or 0.0) <= 0.0:
            style_dist["noisy"] = 0.0

        if float(global_style_dist.get("mixed", 1.0) or 0.0) <= 0.0:
            style_dist["mixed"] = 0.0


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

    babel_mode_prob = float(text_cfg.get("babel_mode_prob", 0.0))
    babel_mode_prob = max(0.0, min(0.25, babel_mode_prob))

    is_babel_mode = rng.random() < babel_mode_prob

    if is_babel_mode and line_kind not in {"title", "caption", "table_cell"}:
        code_switch_prob = rng.uniform(0.12, 0.28)
    else:
        code_switch_prob = float(
            text_cfg.get(
                "code_switch_prob",
                0.03 if style == "mixed" else 0.0,
            )
        )


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

    if (
        text_provider is not None
        and style in {"prose", "mixed"}
        and line_kind in {"text", "paragraph"}
    ):
        provided_line = _provider_token_or_empty(
            text_provider,
            line_kind=line_kind,
            style=style,
        )

        fitted_line = _fit_provider_text_to_width(
            draw,
            font,
            provided_line,
            max_width_px,
            min_words=4,
        )

        if fitted_line:
            return fitted_line, script


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
        target_tokens = max(1, min(target_tokens, rng.randint(1, 5)))

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



