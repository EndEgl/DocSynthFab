# src/ai1_gen/render/page_renderer.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - Pillow>=10,<12

from __future__ import annotations

from typing import Any, Dict
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ai1_gen.layout.layout_sampler import PageSpec
from ai1_gen.latex.miktex_render import render_latex_to_rgba, LatexRenderError, sample_latex_expr


# -------------------------
# UTF-8 Text Synth (meaningful + gibberish)
# -------------------------

# Küçük ama yeterli “meaningful” sözlükler (isteyince büyütürüz)
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
_WORDS_RU = [
    "пример", "решение", "данные", "модель", "строка", "качество",
]
_WORDS_EL = [
    "παράδειγμα", "λύση", "δεδομένα", "μοντέλο",
]
_WORDS_AR = [
    "مثال", "حل", "بيانات", "نموذج", "سطر",
]

# Unicode “script” havuzları: kontrollü aralıklar (kontrol karakter yok)
_LATIN_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_TR_EXTRA = "çÇğĞıİöÖşŞüÜ"
_DE_EXTRA = "äÄöÖüÜß"
_DIGITS = "0123456789"
_PUNCT = ".,;:!?()[]{}<>+-=*/_~'\"@#&%$"
_SPACES = [" ", "  ", "   ", "\t"]  # OCR için spacing varyasyonu

# Cyrillic (basic)
_CYR_START, _CYR_END = 0x0410, 0x044F  # А-я
# Greek (basic)
_GR_START, _GR_END = 0x0391, 0x03C9  # Α-ω
# Arabic (basic)
_AR_START, _AR_END = 0x0621, 0x064A  # ء-ي

# “symbol” (matematik dışı ama OCR’ı zorlayan)
_SYMBOLS = "±×÷≤≥≈≠∑∏√∞∂∇∈∉∩∪→←↔°"


def _rand_from_range(rng: random.Random, a: int, b: int, k: int) -> str:
    return "".join(chr(rng.randint(a, b)) for _ in range(k))


def _pick_script(rng: random.Random, dist: Dict[str, float]) -> str:
    # dist normalize değilse bile toleranslı
    items = list(dist.items())
    s = sum(max(0.0, float(p)) for _, p in items) or 1.0
    r = rng.random() * s
    acc = 0.0
    for k, p in items:
        acc += max(0.0, float(p))
        if r <= acc:
            return str(k)
    return str(items[-1][0])


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> float:
    # Pillow sürümlerine göre değişebiliyor; güvenli ölçüm
    try:
        return float(draw.textlength(text, font=font))
    except Exception:
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return float(bbox[2] - bbox[0])
        except Exception:
            # en kötü tahmin
            return float(len(text) * 10)


def _safe_font(fonts_dir: str | None, size: int) -> ImageFont.ImageFont:
    # 1) proje fonts_dir
    candidates = [
        "NotoSans-Regular.ttf",
        "NotoSans.ttf",
        "DejaVuSans.ttf",
        "Arial.ttf",
        "LiberationSans-Regular.ttf",
        "segoeui.ttf",          # Windows
        "seguisym.ttf",         # Windows symbols
        "arialuni.ttf",         # Arial Unicode (varsa)
    ]

    # fonts_dir taraması
    if fonts_dir:
        p = Path(fonts_dir)
        if p.exists():
            for cand in candidates:
                fp = p / cand
                if fp.exists():
                    try:
                        return ImageFont.truetype(str(fp), size=size)
                    except Exception:
                        pass

    # 2) Windows Fonts fallback (varsa)
    win_fonts = Path(r"C:\Windows\Fonts")
    if win_fonts.exists():
        for cand in candidates:
            fp = win_fonts / cand
            if fp.exists():
                try:
                    return ImageFont.truetype(str(fp), size=size)
                except Exception:
                    pass

    # 3) last resort
    return ImageFont.load_default()


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
    # default
    pool = _LATIN_CHARS + _DIGITS
    return "".join(rng.choice(pool) for _ in range(n))


def _make_line_text(
    rng: random.Random,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    max_width_px: int,
    *,
    density_level: str,
    noise_level: str,
    text_cfg: Dict[str, Any],
) -> str:
    """
    UTF-8 line synth:
      - meaningful words + gibberish + punctuation + random spacing
      - fits roughly in bbox width
    """
    # default dist: latin ağırlıklı ama karışık
    dist = text_cfg.get("scripts_dist", {
        "latin": 0.45,
        "tr": 0.18,
        "de": 0.07,
        "ru": 0.10,
        "el": 0.06,
        "ar": 0.09,
        "symbols": 0.05,
    })
    script = _pick_script(rng, dist)

    # “anlamlı / anlamsız” karışımı
    p_mean = float(text_cfg.get("meaningful_prob", 0.55))
    p_gibb = float(text_cfg.get("gibberish_prob", 0.35))
    # kalan -> mixed

    # satır uzunluğu: density’ye göre
    if density_level == "dense":
        target_tokens = rng.randint(8, 18)
    elif density_level == "sparse":
        target_tokens = rng.randint(3, 8)
    else:
        target_tokens = rng.randint(6, 14)

    # noise_level heavy ise daha “weird” karakter + punctuation
    punct_boost = 1.0
    if noise_level == "heavy":
        punct_boost = 1.6
    elif noise_level == "clean":
        punct_boost = 0.7

    parts: list[str] = []
    for _ in range(target_tokens):
        r = rng.random()
        if r < p_mean:
            tok = _rand_word_meaningful(rng, script)
        elif r < p_mean + p_gibb:
            tok = _rand_gibberish(rng, script, rng.randint(2, 10))
        else:
            # mixed token: word + digits + symbols
            base = _rand_word_meaningful(rng, script)
            suffix = _rand_gibberish(rng, "symbols" if rng.random() < 0.4 else script, rng.randint(1, 4))
            tok = base + suffix

        # bazen punctuation ekle
        if rng.random() < 0.22 * punct_boost:
            tok = tok + rng.choice(list(_PUNCT))
        parts.append(tok)

        # random spacing (tab dahil)
        if rng.random() < 0.35:
            parts.append(rng.choice(_SPACES))
        else:
            parts.append(" ")

    text = "".join(parts).strip()

    # bbox içine sığdır (sağdan kırp)
    # (çok sık ölçüm pahalı; ama güvenli olması için birkaç iterasyon yapıyoruz)
    if max_width_px <= 30:
        return text[: max(1, len(text) // 2)], script


        
    for _ in range(6):
        wpx = _measure_text(draw, text, font)
        if wpx <= max_width_px:
            break
        # fazla uzun -> kırp
        text = text[: max(1, int(len(text) * 0.85))].rstrip()

    return text, script


# -------------------------
# Renderer
# -------------------------

def render_page_layers(page_spec: PageSpec, cfg, rng: random.Random) -> Dict[str, Any]:
    w, h = page_spec.w, page_spec.h
    bg = tuple(int(x) for x in cfg.raw.get("page", {}).get("bg_color_rgb", [255, 255, 255]))

    # base image (RGB)
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    # masks
    mask_text = Image.new("L", (w, h), 0)
    mask_math = Image.new("L", (w, h), 0)
    mdraw_t = ImageDraw.Draw(mask_text)
    mdraw_m = ImageDraw.Draw(mask_math)

    render_cfg = cfg.render()
    fonts_dir = render_cfg.get("text", {}).get("fonts_dir", None)

    text_cfg = render_cfg.get("text", {})
    # UTF-8 mod: burada ürettiğimiz metin zaten unicode string; asıl mesele font
    # text_cfg["lang_mode"] = "utf8" varsayılıyor.

    style_cfg = cfg.raw.get("style", {})
    base_size = int(14 * (page_spec.dpi / 300.0))
    if page_spec.density_level == "dense":
        base_size = max(10, base_size - 2)
    elif page_spec.density_level == "sparse":
        base_size = base_size + 1

    # hires_crop: bazı bloklarda zorunlu local scale (büyük/küçük karışık)
    local_scale_prob = float(style_cfg.get("local_scale_mode_prob", 0.35))
    enforce_local = (page_spec.scale_profile == "hires_crop")

    # non-text layer (figure/table lines/watermark) -> maskte 0 kalmalı
    non_text_cfg = render_cfg.get("non_text", {})
    if bool(non_text_cfg.get("enable", True)):
        if rng.random() < float(non_text_cfg.get("watermark_prob", 0.10)):
            for k in range(0, w, max(200, w // 12)):
                draw.line((k, 0, k + h, h), fill=(240, 240, 240), width=3)

        if page_spec.has_figure and rng.random() < float(non_text_cfg.get("figure_shape_prob", 0.25)):
            x0 = int(0.15 * w)
            y0 = int(0.55 * h)
            x1 = int(0.85 * w)
            y1 = int(0.80 * h)
            draw.rectangle((x0, y0, x1, y1), outline=(60, 60, 60), width=4)

    # Block font cache (block_id -> font)
    block_font: dict[int, ImageFont.ImageFont] = {}

    gt_line_text: dict[int, str] = {}
    gt_line_script: dict[int, str] = {}
    gt_line_latex: dict[int, str] = {}
    gt_script_hist: dict[str, int] = {}



    # Render blocks (table lines etc.)
    for b in page_spec.blocks:
        bx, by, bw, bh = b.bbox

        use_local = enforce_local or (rng.random() < local_scale_prob)
        size_pt = base_size
        if use_local:
            if rng.random() < 0.5:
                size_pt = max(9, base_size - 3)
            else:
                size_pt = base_size + 6

        font = _safe_font(fonts_dir, size=size_pt)
        block_font[b.block_id] = font

        if b.block_type == "table" and page_spec.has_table:
            if rng.random() < float(non_text_cfg.get("table_line_prob", 0.30)):
                cols = 3
                rows = 4
                for i in range(1, cols):
                    x = bx + i * bw // cols
                    draw.line((x, by, x, by + bh), fill=(80, 80, 80), width=2)
                for j in range(1, rows):
                    y = by + j * bh // rows
                    draw.line((bx, y, bx + bw, y), fill=(80, 80, 80), width=2)

    # LaTeX config
    latex_cfg = render_cfg.get("latex", {})
    latex_enable = bool(latex_cfg.get("enable", True))
    pdflatex_cmd = latex_cfg.get("compiler", "pdflatex")
    timeout_s = int(latex_cfg.get("timeout_s", 12))
    raster_dpi = int(latex_cfg.get("raster_dpi", 300))

    # Lines
    for ln in page_spec.lines:
        x, y, ww, hh = ln.bbox
        if ww <= 5 or hh <= 5:
            continue

        if ln.line_type == "math":
            # Math: mask_math 255, image’e latex raster yapıştır
            mdraw_m.rectangle((x, y, x + ww, y + hh), fill=255)

            if latex_enable:
                expr = sample_latex_expr(rng, level=page_spec.noise_level)
                gt_line_latex[ln.line_id] = expr
                gt_script_hist["math"] = gt_script_hist.get("math", 0) + 1
                
                try:
                    eq = render_latex_to_rgba(
                        expr,
                        pdflatex_cmd=pdflatex_cmd,
                        timeout_s=timeout_s,
                        raster_dpi=raster_dpi,
                    )
                    eq = eq.convert("RGBA")
                    eq = eq.resize((max(10, ww), max(10, hh)), resample=Image.Resampling.LANCZOS)
                    img.paste(eq, (x, y), eq)
                except LatexRenderError:
                    # fallback text
                    draw.text((x, y), "math", fill=(0, 0, 0))
            else:
                draw.text((x, y), "math", fill=(0, 0, 0))

        else:
            # text/caption/table_cell
            mdraw_t.rectangle((x, y, x + ww, y + hh), fill=255)

            font = block_font.get(ln.block_id, ImageFont.load_default())

            # biraz padding
            px = x
            py = y

            s, script = _make_line_text(
                rng,
                draw,
                font,
                max_width_px=max(10, ww - 2),
                density_level=page_spec.density_level,
                noise_level=page_spec.noise_level,
                text_cfg=text_cfg,
            )

            gt_line_text[ln.line_id] = s
            gt_line_script[ln.line_id] = script
            gt_script_hist[script] = gt_script_hist.get(script, 0) + 1
            
            
            draw.text((px, py), s, fill=(0, 0, 0), font=font)

    # Export-ready numpy
    image_u8 = np.array(img, dtype=np.uint8)
    mask_text_u8 = np.array(mask_text, dtype=np.uint8)
    mask_math_u8 = np.array(mask_math, dtype=np.uint8)

    # binary enforce
    mask_text_u8 = np.where(mask_text_u8 > 0, 255, 0).astype(np.uint8)
    mask_math_u8 = np.where(mask_math_u8 > 0, 255, 0).astype(np.uint8)

    ann = {
        "version": "ai1-ds-v1.3.2",
        "page_id": page_spec.page_id,
        "size": {"w": w, "h": h, "dpi": page_spec.dpi},
        "meta": {
            "layout_type": page_spec.layout_type,
            "noise_level": page_spec.noise_level,
            "density_level": page_spec.density_level,
            "scale_profile": page_spec.scale_profile,
            "has_table": page_spec.has_table,
            "has_equation": page_spec.has_equation,
            "has_figure": page_spec.has_figure,
            "rotation_deg": page_spec.rotation_deg,
            "perspective": bool(page_spec.perspective),
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
        ],
        "lines": [
            {
                "line_id": ln.line_id,
                "block_id": ln.block_id,
                "line_type": ln.line_type,
                "line_order_in_block": ln.line_order_in_block,
                "global_line_order": ln.global_line_order,
                "bbox": list(ln.bbox),
                "quad": ln.quad,
                "is_hard": bool(ln.is_hard),
            }
            for ln in page_spec.lines
        ],
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
        [(ln["global_line_order"], ln.get("gt_text", "")) for ln in ann["lines"] if "gt_text" in ln],
        key=lambda x: x[0],
    )
    ann["gt_page_text"] = "\n".join(t for _, t in ordered).strip()

    ann["gt_stats"] = {
        "scripts_hist": gt_script_hist,
        "has_gt_text_lines": sum(1 for ln in ann["lines"] if "gt_text" in ln),
        "has_gt_math_lines": sum(1 for ln in ann["lines"] if "gt_latex" in ln),
    }


    return {
        "image_u8": image_u8,
        "mask_text_u8": mask_text_u8,
        "mask_math_u8": mask_math_u8,
        "ann": ann,
    }