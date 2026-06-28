# src/docsynthfab/render/page_renderer.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - Pillow>=10,<12

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw

from docsynthfab.content import ensure_content_bank, TextProvider
from docsynthfab.latex.miktex_render import check_latex_http_health, sample_latex_expr
from docsynthfab.layout.layout_sampler import PageSpec

from .draw_utils import (
    _draw_text_glyph_mask,
    _measure_text,
    _paste_alpha_as_binary,
    _sample_contrast_color,
)
from .figure_renderer import _make_random_figure_patch
from .font_size import sample_font_size_px
from .font_utils import (
    _fit_font_to_bbox_height,
    _font_height_px,
    _font_supports_text,
    _safe_font_for_text,
    _sample_probe_text_for_script,
)
from .geometry_utils import (
    _clamp_box,
    _collect_block_line_map,
    _intersects,
    _jump_past_obstacle,
    _line_kind_from_block,
    _pad_box,
    _try_relocate_line_bbox_down,
)
from .latex_rendering import (
    _draw_math_fallback_text,
    _normalize_latex_expr,
    _render_latex_with_retries,
    _resolve_latex_cfg,
)
from .table_renderer import _draw_table_structure
from .text_synth import (
    _choose_script_for_line,
    _content_pure_mode_from_cfg,
    _make_line_text,
)


def _rendered_text_bbox_xywh(
    draw,
    *,
    x: int,
    y: int,
    text: str,
    font,
    page_w: int,
    page_h: int,
    pad_x: int = 2,
    pad_y: int = 1,
) -> Tuple[int, int, int, int]:
    """
    Return a tight-ish bbox for the actual rendered text, not the whole line slot.
    """
    text = str(text or "")

    try:
        x0, y0, x1, y1 = draw.textbbox((int(x), int(y)), text, font=font)
    except Exception:
        try:
            tw = int(round(draw.textlength(text, font=font)))
        except Exception:
            tw = 10

        th = int(getattr(font, "size", 10) * 1.25)
        x0, y0, x1, y1 = int(x), int(y), int(x) + max(4, tw), int(y) + max(4, th)

    x0 = max(0, int(x0) - pad_x)
    y0 = max(0, int(y0) - pad_y)
    x1 = min(int(page_w), int(x1) + pad_x)
    y1 = min(int(page_h), int(y1) + pad_y)

    return (
        int(x0),
        int(y0),
        max(4, int(x1 - x0)),
        max(4, int(y1 - y0)),
    )

def _script_family_for_char(ch: str) -> str | None:
    cp = ord(ch)

    # Latin + Latin extended: TR/DE/FR/ES included.
    if (
        0x0041 <= cp <= 0x007A
        or 0x00C0 <= cp <= 0x024F
        or 0x1E00 <= cp <= 0x1EFF
    ):
        return "latin"

    if 0x0370 <= cp <= 0x03FF:
        return "el"

    if 0x0400 <= cp <= 0x052F:
        return "ru"

    if 0x0590 <= cp <= 0x05FF:
        return "he"

    if 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F:
        return "ar"

    if 0x0900 <= cp <= 0x097F:
        return "hi"

    if 0x3040 <= cp <= 0x30FF:
        return "ja"

    if 0x4E00 <= cp <= 0x9FFF:
        return "zh"

    if 0xAC00 <= cp <= 0xD7AF:
        return "ko"

    if 0x0E00 <= cp <= 0x0E7F:
        return "th"

    return None


def _script_families_in_text(text: str) -> Dict[str, int]:
    out: Dict[str, int] = {}

    for ch in str(text or ""):
        fam = _script_family_for_char(ch)

        if fam is None:
            continue

        out[fam] = out.get(fam, 0) + 1

    return out


def _has_unsafe_script_mix(text: str) -> bool:
    families = _script_families_in_text(text)

    if len(families) <= 1:
        return False

    total = sum(families.values())

    if total <= 0:
        return False

    # Allow tiny accidental traces, but reject real mixed-script lines.
    strong = [k for k, v in families.items() if (v / total) >= 0.08]

    return len(strong) >= 2

def _dominant_script_family(text: str, fallback: str = "latin") -> str:
    families = _script_families_in_text(text)

    if not families:
        return str(fallback or "latin")

    return max(families.items(), key=lambda kv: int(kv[1]))[0]


def _select_font_for_final_text(
    *,
    fonts_dir: str | None,
    desired_size: int,
    bbox_h: int,
    rng: random.Random,
    text: str,
    script: str,
    role: str,
) -> tuple[Any, str]:
    """
    Final metin üretildikten sonra fontu yeniden seçer.

    Önemli:
    - İlk seçilen script ile final metnin gerçek script'i farklı olabilir.
    - _font_supports_text bazı fontlarda tofu/kare glyph için yanlış True dönebilir.
    - Bu yüzden final text belli olduktan sonra font her zaman yeniden seçilir.
    """
    final_script = _dominant_script_family(text, fallback=script)

    fnt = _fit_font_to_bbox_height(
        fonts_dir,
        desired_size=desired_size,
        bbox_h=bbox_h,
        rng=rng,
        script=final_script,
        role=role,
        probe_text=text,
    )

    return fnt, final_script

def _has_unsafe_ocr_text_noise(text: str) -> bool:
    """
    Reject code/noisy stress tokens in the main OCR web generator path.

    This is a backend safety net. GUI defaults should avoid these already,
    but renderer-level validation prevents bad config changes from leaking
    visually broken OCR lines.
    """
    import re
    import unicodedata

    s = str(text or "")

    if not s.strip():
        return True

    unsafe_visual_chars = set("□▯▢■▪▫◻◼\uFFFD●○◆◇◾◽◦")
    if any(ch in unsafe_visual_chars for ch in s):
        return True

    # Reject Unicode symbol/control/private-surrogate leakage.
    for ch in s:
        cat = unicodedata.category(ch)
        if cat in {"So", "Co", "Cc", "Cs"}:
            return True

    # Obvious code/config/noisy leakage.
    if re.search(
        r"(__|::|==|!=|\+=|-=|[<>{}\[\]\|]|[□▯▢■▪▫◻◼\uFFFD●○◆◇◾◽◦]|DATA|MODEL|TEMPOR|DOLOR|INCIDIDUNT|ACCURACY|VALID|TRAIN|LOSS)",
        s,
        flags=re.IGNORECASE,
    ):
        return True

    # Random alphanumeric chunks, e.g. xÜnXüFC1GÄ, Q7, r7SQFL4uH2B.
    if re.search(r"[A-Za-zÀ-ſ]{2,}\d+[A-Za-zÀ-ſ0-9]{1,}", s):
        return True

    # Too much math/operator noise in a text OCR line.
    noisy_chars = sum(
        1
        for ch in s
        if ch in "∑∏∂∇∞≈≠≤≥±÷×∪∩↔←→{}[]<>|%$#@&*~^"
    )

    if re.search(r"[∑∏∂∇∞≈≠≤≥±÷×∪∩↔←→]{2,}", s):
        return True

    # Random alphanumeric chunks with embedded digits, e.g. Q7, r7SQFL4uH2B.
    # Do not reject ordinary long words such as "normal" or "document".
    if re.search(r"\b[A-Za-zÀ-ſА-Яа-я]+[0-9]+[A-Za-zÀ-ſА-Яа-я0-9]*\b", s):
        return True

    visible_chars = sum(1 for ch in s if not ch.isspace())

    if visible_chars > 0 and (noisy_chars / visible_chars) > 0.03:
        return True

    return False

def _safe_ocr_fallback_text(
    script: str,
    line_kind: str = "text",
    line_id: int = 0,
) -> str:
    script = str(script or "latin").strip().lower()
    line_kind = str(line_kind or "text").strip().lower()

    samples = {
        "latin": [
            "example data line",
            "document reference number",
            "sample page text",
            "quality control record",
        ],
        "tr": [
            "örnek veri satırı",
            "belge kayıt numarası",
            "kalite kontrol notu",
            "sayfa metin örneği",
        ],
        "de": [
            "Beispiel Daten Zeile",
            "Dokument Referenz Nummer",
            "Qualität Prüfung Bericht",
            "Seite Text Beispiel",
        ],
        "ru": [
            "пример строка данные",
            "документ номер запись",
            "качество проверка отчет",
            "страница текст пример",
        ],
        "el": [
            "παράδειγμα γραμμή δεδομένα",
            "έγγραφο αριθμός αναφορά",
            "ποιότητα έλεγχος αναφορά",
            "σελίδα κείμενο παράδειγμα",
        ],
        "ar": [
            "مثال بيانات سطر",
            "وثيقة رقم مرجع",
            "تقرير فحص جودة",
            "نص صفحة مثال",
        ],
        "he": [
            "דוגמה נתונים שורה",
            "מסמך מספר הפניה",
            "דוח בדיקת איכות",
            "טקסט עמוד לדוגמה",
        ],
        "hi": [
            "उदाहरण डेटा पंक्ति",
            "दस्तावेज़ संदर्भ संख्या",
            "गुणवत्ता जांच रिपोर्ट",
            "पृष्ठ पाठ उदाहरण",
        ],
        "zh": [
            "示例 数据 行",
            "文档 参考 编号",
            "质量 检查 报告",
            "页面 文本 示例",
        ],
        "ja": [
            "サンプル データ 行",
            "文書 参照 番号",
            "品質 確認 報告",
            "ページ テキスト 例",
        ],
        "ko": [
            "예시 데이터 행",
            "문서 참조 번호",
            "품질 검사 보고",
            "페이지 텍스트 예시",
        ],
        "th": [
            "ตัวอย่าง ข้อมูล บรรทัด",
            "เอกสาร หมายเลข อ้างอิง",
            "รายงาน ตรวจสอบ คุณภาพ",
            "ตัวอย่าง ข้อความ หน้า",
        ],
    }

    arr = samples.get(script) or samples.get("latin", ["example data line"])
    idx = abs(int(line_id)) % len(arr)

    if line_kind == "title" and script in {"latin", "tr", "de"}:
        return arr[idx].title()

    return arr[idx]


def _box_overlap_ratio_min_area(
    a: Tuple[int, int, int, int],
    b: Tuple[int, int, int, int],
) -> float:
    ax0, ay0, aw, ah = [int(v) for v in a]
    bx0, by0, bw, bh = [int(v) for v in b]

    ax1 = ax0 + max(0, aw)
    ay1 = ay0 + max(0, ah)
    bx1 = bx0 + max(0, bw)
    by1 = by0 + max(0, bh)

    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)

    iw = max(0, ix1 - ix0)
    ih = max(0, iy1 - iy0)

    inter = iw * ih

    if inter <= 0:
        return 0.0

    area_a = max(1, aw * ah)
    area_b = max(1, bw * bh)

    return float(inter) / float(min(area_a, area_b))


def _has_excessive_text_overlap(
    box: Tuple[int, int, int, int],
    obstacles: List[Tuple[int, int, int, int]],
    *,
    max_ratio: float = 0.05,
) -> bool:
    for ob in obstacles:
        if _box_overlap_ratio_min_area(box, ob) > float(max_ratio):
            return True

    return False


def render_page_layers(page_spec: PageSpec, cfg: Any, rng: random.Random) -> Dict[str, Any]:
    page_cfg = (cfg.raw.get("page", {}) or {}) if hasattr(cfg, "raw") else {}
    render_cfg = cfg.render()
    text_cfg = render_cfg.get("text", {}) or {}

    safe_ocr_line_guard = bool(text_cfg.get("safe_ocr_line_guard", True))
    reject_overlapping_text = bool(text_cfg.get("reject_overlapping_text", False))

    max_text_generation_attempts = int(
        text_cfg.get("max_text_generation_attempts", 6) or 6
    )
    max_text_generation_attempts = max(1, min(max_text_generation_attempts, 20))

    unsafe_retry_policy = str(
        text_cfg.get("unsafe_retry_policy", "skip") or "skip"
    ).strip().lower()

    safe_fallback_after_retries = bool(
        text_cfg.get("safe_fallback_after_retries", False)
    )

    reject_pil_default_font = bool(
        text_cfg.get("reject_pil_default_font", False)
    )    
    
    non_text_cfg = render_cfg.get("non_text", {}) or {}
    style_cfg = (cfg.raw.get("style", {}) or {}) if hasattr(cfg, "raw") else {}

    content_cfg = (cfg.raw.get("content", {}) or {}) if hasattr(cfg, "raw") else {}
    content_pure_mode = _content_pure_mode_from_cfg(content_cfg)

    content_paths = ensure_content_bank(cfg)

    text_provider = TextProvider.from_json(
        content_paths["generated_json"],
        content_cfg,
        rng,
    )

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
    book_enable = (
        bool(book_cfg.get("enable", True))
        and page_spec.page_family == "book"
        and content_pure_mode in {"text_only", "mixed"}
    )

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

    gt_line_text = {}
    gt_line_script = {}
    gt_line_font_support = {}
    gt_line_script_families = {}
    gt_line_font_path = {}
    gt_line_font_index = {}
    gt_line_font_name = {}

    gt_line_latex: Dict[int, str] = {}
    gt_script_hist: Dict[str, int] = {}

    latex_render_errors: List[Dict[str, Any]] = []

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
    enforce_local = page_spec.scale_profile == "hires_crop"

    latex_runtime_cfg = _resolve_latex_cfg(render_cfg)

    latex_enable = bool(latex_runtime_cfg["enable"])
    latex_backend = str(latex_runtime_cfg["backend"])
    latex_http_base_url = str(latex_runtime_cfg["http_base_url"])
    pdflatex_cmd = str(latex_runtime_cfg["compiler"])
    timeout_s = int(latex_runtime_cfg["timeout_s"])
    raster_dpi = int(latex_runtime_cfg["raster_dpi"])
    latex_level = str(latex_runtime_cfg["level"])
    allowed_ops = latex_runtime_cfg["allowed_ops"]
    latex_draw_fallback_expr = bool(latex_runtime_cfg["draw_fallback_expr"])

    if latex_enable and bool(latex_runtime_cfg["health_check"]):
        latex_enable = check_latex_http_health(
            http_base_url=latex_http_base_url,
            timeout_s=min(5.0, float(timeout_s)),
        )

    relocated_bbox_by_line_id: Dict[int, Tuple[int, int, int, int]] = {}
    block_line_map = _collect_block_line_map(page_spec)

    # --------------------------------------------------
    # PASS 1: Block-aware render.
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
    # PASS 2: Line render using PageSpec.
    # --------------------------------------------------
    for ln in page_spec.lines:
        x, y, ww, hh = ln.bbox

        if ww <= 6 or hh <= 6:
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
                x,
                y,
                ww,
                hh,
                hard_obstacles,
                w=w,
                h=h,
                y_max=yB,
                tries=10,
                gap=jump_gap_px,
            )

            if not ok:
                continue

        relocated_bbox_by_line_id[int(ln.line_id)] = (int(x), int(y), int(ww), int(hh))
        lbox = (x, y, x + ww, y + hh)

        if ln.line_type == "math":
            actual_has_equation = True

            expr = _normalize_latex_expr(
                sample_latex_expr(
                    rng,
                    level=latex_level,
                    allowed_ops=allowed_ops,
                )
            )

            gt_line_latex[int(ln.line_id)] = expr
            gt_script_hist["math"] = gt_script_hist.get("math", 0) + 1

            rendered_ok = False

            if latex_enable:
                rendered_ok, rendered_expr, eq, retry_errors = _render_latex_with_retries(
                    initial_expr=expr,
                    rng=rng,
                    latex_level=latex_level,
                    allowed_ops=allowed_ops,
                    pdflatex_cmd=pdflatex_cmd,
                    timeout_s=timeout_s,
                    raster_dpi=raster_dpi,
                    latex_backend=latex_backend,
                    latex_http_base_url=latex_http_base_url,
                    target_w=ww,
                    target_h=hh,
                    random_offset=True,
                )

                if rendered_ok and eq is not None:
                    expr = rendered_expr
                    gt_line_latex[int(ln.line_id)] = expr
                    img.paste(eq, (x, y), eq)
                    _paste_alpha_as_binary(mask_math, eq.split()[-1], x, y)
                else:
                    latex_render_errors.append({
                        "line_id": int(ln.line_id),
                        "expr": str(expr),
                        "error": "latex-render-all-retries-failed",
                        "retry_errors": retry_errors[:6],
                    })

            if not rendered_ok:
                if latex_draw_fallback_expr:
                    _draw_math_fallback_text(
                        draw,
                        mdraw_m,
                        x=x,
                        y=y,
                        ww=ww,
                        hh=hh,
                        expr=expr,
                        fonts_dir=fonts_dir,
                        base_size=base_size,
                        rng=rng,
                        style_cfg=style_cfg,
                    )
                else:
                    # If fallback drawing is disabled, still keep gt_latex.
                    pass

            hard_obstacles.append(_pad_box(lbox, 5, w, h))
            continue

        sampled_font_size = sample_font_size_px(rng, cfg)
        bbox_limited_size = max(8, int(hh * 0.95))
        desired = min(sampled_font_size, bbox_limited_size)

        if enforce_local or rng.random() < local_scale_prob:
            desired = int(desired * rng.uniform(0.82, 1.22))

        desired = max(6, min(desired, bbox_limited_size))


        role = "body"

        if line_kind == "title":
            role = "title"
        elif line_kind == "caption":
            role = "caption"
        elif line_kind == "table_cell":
            role = "table"
        elif line_kind == "list":
            role = "list"

        script = _choose_script_for_line(rng, text_cfg, line_kind=line_kind)

        fnt = _fit_font_to_bbox_height(
            fonts_dir,
            desired_size=desired,
            bbox_h=hh,
            rng=rng,
            script=script,
            role=role,
            probe_text=_sample_probe_text_for_script(script, role),
        )

        s = ""
        original_script = script

        for attempt_i in range(max_text_generation_attempts):
            use_provider = text_provider if attempt_i == 0 else None

            s_candidate, script_candidate = _make_line_text(
                rng,
                draw,
                fnt,
                max_width_px=max(10, ww),
                density_mode=page_spec.density_level,
                noise_level=page_spec.noise_level,
                text_cfg=text_cfg,
                text_provider=use_provider,
                line_kind=line_kind,
                page_family=page_spec.page_family,
                forced_script=original_script,
            )

            if not s_candidate:
                continue

            if safe_ocr_line_guard:
                if _has_unsafe_script_mix(s_candidate):
                    continue

                if _has_unsafe_ocr_text_noise(s_candidate):
                    continue

            s = s_candidate
            script = _dominant_script_family(s_candidate, fallback=script_candidate)
            break

        if not s:
            use_safe_fallback = (
                safe_fallback_after_retries
                and unsafe_retry_policy == "safe_fallback"
            )

            latex_render_errors.append({
                "line_id": int(ln.line_id),
                "expr": "",
                "error": "text-generation-safe-fallback-used"
                if use_safe_fallback
                else "text-generation-unsafe-after-retries",
                "script": str(original_script),
                "line_kind": str(line_kind),
                "safe_ocr_line_guard": bool(safe_ocr_line_guard),
            })

            if use_safe_fallback:
                script = str(original_script or "latin")
                s = _safe_ocr_fallback_text(
                    script=script,
                    line_kind=line_kind,
                    line_id=int(ln.line_id),
                )
            else:
                continue




        fnt, script = _select_font_for_final_text(
            fonts_dir=fonts_dir,
            desired_size=desired,
            bbox_h=hh,
            rng=rng,
            text=s,
            script=script,
            role=role,
        )

        font_path_for_check = str(
            getattr(fnt, "_docsynthfab_font_path", "")
            or getattr(fnt, "path", "")
            or ""
        )

        if reject_pil_default_font and font_path_for_check == "__PIL_DEFAULT__":
            latex_render_errors.append({
                "line_id": int(ln.line_id),
                "expr": "",
                "error": "pil-default-font-rejected",
                "script": str(script),
                "text_sample": str(s[:120]),
            })

            if safe_fallback_after_retries and unsafe_retry_policy == "safe_fallback":
                s = _safe_ocr_fallback_text(
                    script=script,
                    line_kind=line_kind,
                    line_id=int(ln.line_id),
                )

                fnt, script = _select_font_for_final_text(
                    fonts_dir=fonts_dir,
                    desired_size=desired,
                    bbox_h=hh,
                    rng=rng,
                    text=s,
                    script=script,
                    role=role,
                )
            else:
                continue


        text_bb = _rendered_text_bbox_xywh(
            draw,
            x=int(x),
            y=int(y),
            text=s,
            font=fnt,
            page_w=w,
            page_h=h,
        )

        if (
            safe_ocr_line_guard
            and reject_overlapping_text
            and _has_excessive_text_overlap(
                text_bb,
                hard_obstacles,
                max_ratio=0.12,
            )
        ):                
            latex_render_errors.append({
                "line_id": int(ln.line_id),
                "expr": "",
                "error": "text-overlap-rejected",
                "script": str(script),
                "bbox": list(text_bb),
            })
            continue

        text_color = _sample_contrast_color(rng, style_cfg)
        _draw_text_glyph_mask(draw, mdraw_t, x, y, s, fnt, text_color)

        relocated_bbox_by_line_id[int(ln.line_id)] = text_bb


        gt_line_text[int(ln.line_id)] = s
        gt_line_script[int(ln.line_id)] = script
        gt_line_font_support[int(ln.line_id)] = bool(_font_supports_text(fnt, s))
        gt_line_script_families[int(ln.line_id)] = _script_families_in_text(s)
        

        try:
            gt_line_font_path[int(ln.line_id)] = str(
                getattr(fnt, "_docsynthfab_font_path", "")
                or getattr(fnt, "path", "")
                or ""
            )
        except Exception:
            gt_line_font_path[int(ln.line_id)] = ""

        try:
            gt_line_font_index[int(ln.line_id)] = int(
                getattr(fnt, "_docsynthfab_font_index", -1)
            )
        except Exception:
            gt_line_font_index[int(ln.line_id)] = -1

        try:
            gt_line_font_name[int(ln.line_id)] = " / ".join(str(x) for x in fnt.getname())
        except Exception:
            gt_line_font_name[int(ln.line_id)] = ""
            
                
        gt_script_hist[script] = gt_script_hist.get(script, 0) + 1

        
        hard_obstacles.append(
            _pad_box(
                (
                    text_bb[0],
                    text_bb[1],
                    text_bb[0] + text_bb[2],
                    text_bb[1] + text_bb[3],
                ),
                5,
                w,
                h,
            )
        )


    # --------------------------------------------------
    # PASS 3: Conservative filler only for sparse book pages.
    # --------------------------------------------------
    if book_enable:
        existing_text_lines = sum(1 for _ln in page_spec.lines if str(_ln.line_type) != "math")

        if existing_text_lines < 8:
            base_font_size = sample_font_size_px(rng, cfg)
            base_font_size = max(6, min(base_font_size, base_size))
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
                        "auto_filler": True,
                    },
                })

                desired_size = base_font_size
                base_font = _safe_font_for_text(
                    fonts_dir,
                    size=desired_size,
                    rng=rng,
                    script="latin",
                    role="body",
                    probe_text="example data line",
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

                        s = ""
                        original_script = script

                        for attempt_i in range(6):
                            use_provider = text_provider if attempt_i == 0 else None

                            s_candidate, script_candidate = _make_line_text(
                                rng,
                                draw,
                                fnt,
                                max_width_px=max(10, maxw - (indent_px if li == 0 else 0)),
                                density_mode=page_spec.density_level,
                                noise_level=page_spec.noise_level,
                                text_cfg=text_cfg,
                                text_provider=use_provider,
                                line_kind="text",
                                page_family=page_spec.page_family,
                                forced_script=original_script,
                            )

                            if not s_candidate:
                                continue

                            if safe_ocr_line_guard:
                                if _has_unsafe_script_mix(s_candidate):
                                    continue

                                if _has_unsafe_ocr_text_noise(s_candidate):
                                    continue

                            s = s_candidate
                            script = _dominant_script_family(s_candidate, fallback=script_candidate)
                            break

                    if not s:
                        if safe_fallback_after_retries and unsafe_retry_policy == "safe_fallback":
                            script = str(original_script or "latin")
                            s = _safe_ocr_fallback_text(
                                script=script,
                                line_kind="text",
                                line_id=int(next_line_id_local),
                            )
                        else:
                            continue


                        fnt, script = _select_font_for_final_text(
                            fonts_dir=fonts_dir,
                            desired_size=desired_size,
                            bbox_h=lh,
                            rng=rng,
                            text=s,
                            script=script,
                            role="body",
                        )


                        filler_bb = _rendered_text_bbox_xywh(
                            draw,
                            x=int(x_text),
                            y=int(ycur),
                            text=s,
                            font=fnt,
                            page_w=w,
                            page_h=h,
                        )

                        if (
                            safe_ocr_line_guard
                            and reject_overlapping_text
                            and _has_excessive_text_overlap(
                                filler_bb,
                                hard_obstacles,
                                max_ratio=0.12,
                            )
                        ):                   
                            ycur += lh
                            continue

                        filler_color = _sample_contrast_color(rng, style_cfg)
                        _draw_text_glyph_mask(draw, mdraw_t, x_text, ycur, s, fnt, filler_color)



                        line_id = next_line_id_local
                        next_line_id_local += 1

                        extra_lines.append({
                            "line_id": line_id,
                            "block_id": block_id,
                            "line_type": "text",
                            "line_order_in_block": in_block,
                            "global_line_order": next_glo_local,
                            "bbox": list(filler_bb),
                            "quad": None,
                            "is_hard": False,
                        })


                        gt_line_text[line_id] = s
                        gt_line_script[line_id] = script
                        gt_line_font_support[line_id] = bool(_font_supports_text(fnt, s))
                        gt_line_script_families[line_id] = _script_families_in_text(s)
                        
                        try:
                            gt_line_font_path[line_id] = str(
                                getattr(fnt, "_docsynthfab_font_path", "")
                                or getattr(fnt, "path", "")
                                or ""
                            )
                        except Exception:
                            gt_line_font_path[line_id] = ""

                        try:
                            gt_line_font_index[line_id] = int(
                                getattr(fnt, "_docsynthfab_font_index", -1)
                            )
                        except Exception:
                            gt_line_font_index[line_id] = -1

                        try:
                            gt_line_font_name[line_id] = " / ".join(str(x) for x in fnt.getname())
                        except Exception:
                            gt_line_font_name[line_id] = ""
                            
                        
                        gt_script_hist[script] = gt_script_hist.get(script, 0) + 1


                        next_glo_local += 1
                        in_block += 1
                        added_here += 1

                        hard_obstacles.append(
                            _pad_box(
                                (
                                    filler_bb[0],
                                    filler_bb[1],
                                    filler_bb[0] + filler_bb[2],
                                    filler_bb[1] + filler_bb[3],
                                ),
                                4,
                                w,
                                h,
                            )
                        )                        
                        ycur += lh

                    ycur += int(lh * para_gap_mult)

            next_block_id = next_block_id_local
            next_line_id = next_line_id_local
            next_glo = next_glo_local

    # -------------------------
    # Export arrays.
    # -------------------------
    image_u8 = np.array(img, dtype=np.uint8)
    mask_text_u8 = np.array(mask_text, dtype=np.uint8)
    mask_math_u8 = np.array(mask_math, dtype=np.uint8)

    mask_text_u8 = np.where(mask_text_u8 > 0, 255, 0).astype(np.uint8)
    mask_math_u8 = np.where(mask_math_u8 > 0, 255, 0).astype(np.uint8)

    # -------------------------
    # Annotation.
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
        "version": "docsynthfab-ds-v0.1",
        "page_id": page_spec.page_id,
        "size": {
            "w": w,
            "h": h,
            "dpi": page_spec.dpi,
            "page_size_name": getattr(page_spec, "page_size_name", None),
            "page_width_in": getattr(page_spec, "page_width_in", None),
            "page_height_in": getattr(page_spec, "page_height_in", None),
            "orientation": getattr(page_spec, "orientation", None),
        },
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
            "text_mode": content_cfg.get("text_mode", "mixed"),
            "text_order": content_cfg.get("text_order", "random"),
            "content_pure_mode": content_pure_mode,
            "content_bank_json": content_paths["generated_json"],

            "latex_render_error_count": int(len(latex_render_errors)),
            "latex_render_errors": latex_render_errors[:20],
            "latex_render_fallback_used": bool(len(latex_render_errors) > 0),
            "latex_render_backend": str(latex_backend),
            "latex_render_http_base_url": str(latex_http_base_url),
            "latex_render_enabled": bool(latex_enable),
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
                item["render_font_supports_text"] = bool(
                    gt_line_font_support.get(lid, False)
                )
                item["render_text_script_families"] = gt_line_script_families.get(
                    lid,
                    {},
                )

                item["render_font_path"] = gt_line_font_path.get(lid, "")
                item["render_font_index"] = gt_line_font_index.get(lid, -1)
                item["render_font_name"] = gt_line_font_name.get(lid, "")

    ordered = sorted(
        [
            (int(ln["global_line_order"]), ln.get("gt_text", ""))
            for ln in ann["lines"]
            if "gt_text" in ln
        ],
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



