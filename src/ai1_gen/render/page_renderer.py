# src/ai1_gen/render/page_renderer.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - Pillow>=10,<12

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw

from ai1_gen.content import ensure_content_bank, TextProvider
from ai1_gen.latex.miktex_render import check_latex_http_health, sample_latex_expr
from ai1_gen.layout.layout_sampler import PageSpec

from .draw_utils import (
    _draw_text_glyph_mask,
    _measure_text,
    _paste_alpha_as_binary,
    _sample_contrast_color,
)
from .figure_renderer import _make_random_figure_patch
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


def render_page_layers(page_spec: PageSpec, cfg: Any, rng: random.Random) -> Dict[str, Any]:
    page_cfg = (cfg.raw.get("page", {}) or {}) if hasattr(cfg, "raw") else {}
    render_cfg = cfg.render()
    text_cfg = render_cfg.get("text", {}) or {}
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

    gt_line_text: Dict[int, str] = {}
    gt_line_script: Dict[int, str] = {}
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

        desired = max(8, int(hh * 0.90))

        if enforce_local or rng.random() < local_scale_prob:
            desired = int(desired * rng.uniform(0.82, 1.22))

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

        s, script = _make_line_text(
            rng,
            draw,
            fnt,
            max_width_px=max(10, ww),
            density_mode=page_spec.density_level,
            noise_level=page_spec.noise_level,
            text_cfg=text_cfg,
            text_provider=text_provider,
            line_kind=line_kind,
            page_family=page_spec.page_family,
            forced_script=script,
        )

        if not _font_supports_text(fnt, s):
            fnt2 = _fit_font_to_bbox_height(
                fonts_dir,
                desired_size=desired,
                bbox_h=hh,
                rng=rng,
                script=script,
                role=role,
                probe_text=s,
            )

            if _font_supports_text(fnt2, s):
                fnt = fnt2
            else:
                latex_render_errors.append({
                    "line_id": int(ln.line_id),
                    "expr": "",
                    "error": "font-coverage-failed",
                    "script": str(script),
                    "text_sample": str(s[:120]),
                })
                continue

        text_color = _sample_contrast_color(rng, style_cfg)
        _draw_text_glyph_mask(draw, mdraw_t, x, y, s, fnt, text_color)

        gt_line_text[int(ln.line_id)] = s
        gt_line_script[int(ln.line_id)] = script
        gt_script_hist[script] = gt_script_hist.get(script, 0) + 1

        hard_obstacles.append(_pad_box(lbox, 5, w, h))

    # --------------------------------------------------
    # PASS 3: Conservative filler only for sparse book pages.
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

                        s, script = _make_line_text(
                            rng,
                            draw,
                            fnt,
                            max_width_px=max(10, maxw - (indent_px if li == 0 else 0)),
                            density_mode=page_spec.density_level,
                            noise_level=page_spec.noise_level,
                            text_cfg=text_cfg,
                            text_provider=text_provider,
                            line_kind="text",
                            page_family=page_spec.page_family,
                            forced_script=script,
                        )

                        if not _font_supports_text(fnt, s):
                            fnt2 = _fit_font_to_bbox_height(
                                fonts_dir,
                                desired_size=desired_size,
                                bbox_h=lh,
                                rng=rng,
                                script=script,
                                role="body",
                                probe_text=s,
                            )

                            if _font_supports_text(fnt2, s):
                                fnt = fnt2
                            else:
                                latex_render_errors.append({
                                    "line_id": int(next_line_id_local),
                                    "expr": "",
                                    "error": "font-coverage-failed-book-filler",
                                    "script": str(script),
                                    "text_sample": str(s[:120]),
                                })
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
                            "bbox": [x_text, ycur, max(10, cx1 - x_text), lh],
                            "quad": None,
                            "is_hard": False,
                        })

                        gt_line_text[line_id] = s
                        gt_line_script[line_id] = script
                        gt_script_hist[script] = gt_script_hist.get(script, 0) + 1

                        next_glo_local += 1
                        in_block += 1
                        added_here += 1

                        hard_obstacles.append(_pad_box((x_text, ycur, x_text + max(10, cx1 - x_text), ycur + lh), 4, w, h))
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
        "version": "ai1-ds-v1.3.2",
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