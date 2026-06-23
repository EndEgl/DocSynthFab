# src/docsynthfab/cli/gt_export.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import Any, Dict


def build_gt_export(ann: Dict[str, Any]) -> Dict[str, Any]:
    meta = ann.get("meta", {}) or {}
    size = ann.get("size", {}) or {}

    blocks_out = []

    for b in ann.get("blocks", []) or []:
        blocks_out.append({
            "block_id": int(b.get("block_id", -1)),
            "block_type": str(b.get("block_type", "")),
            "block_order": int(b.get("block_order", -1)),
            "column_id": int(b.get("column_id", -1)),
            "bbox": b.get("bbox", [0, 0, 0, 0]),
        })

    lines_out = []

    for ln in ann.get("lines", []) or []:
        item = {
            "line_id": int(ln.get("line_id", -1)),
            "block_id": int(ln.get("block_id", -1)),
            "line_type": str(ln.get("line_type", "")),
            "global_line_order": int(ln.get("global_line_order", -1)),
            "bbox": ln.get("bbox", [0, 0, 0, 0]),
        }

        if "gt_text" in ln:
            item["text"] = ln.get("gt_text", "")
            item["script"] = ln.get("gt_script", "unknown")

        if "gt_latex" in ln:
            item["latex"] = ln.get("gt_latex", "")

        lines_out.append(item)

    page_text = ann.get("gt_page_text", "")

    if not page_text:
        ordered = sorted(
            [(x.get("global_line_order", 0), x.get("text", "")) for x in lines_out if x.get("text")],
            key=lambda t: int(t[0]),
        )
        page_text = "\n".join(t for _, t in ordered).strip()

    return {
        "version": ann.get("version", "docsynthfab-ds-v0.1"),
        "page_id": ann.get("page_id", ""),
        "size": {
            "w": int(size.get("w", 0)),
            "h": int(size.get("h", 0)),
            "dpi": int(size.get("dpi", 0)),
            "page_size_name": size.get("page_size_name", None),
            "page_width_in": size.get("page_width_in", None),
            "page_height_in": size.get("page_height_in", None),
            "orientation": size.get("orientation", None),
        },
        "meta": {
            "layout_type": meta.get("layout_type", None),
            "density_level": meta.get("density_level", None),
            "scale_profile": meta.get("scale_profile", None),
            "noise_level": meta.get("noise_level", None),
            "page_family": meta.get("page_family", None),
            "_fallback": meta.get("_fallback", False),
            "_augment_disabled_by_retry": meta.get("_augment_disabled_by_retry", None),
            "_fallback_from_qc_code": meta.get("_fallback_from_qc_code", None),
            "_fallback_from_qc_extra": meta.get("_fallback_from_qc_extra", None),
            "_fallback_from_exception": meta.get("_fallback_from_exception", None),
            "has_table": meta.get("has_table", None),
            "has_equation": meta.get("has_equation", None),
            "has_equation_layout": meta.get("has_equation_layout", None),
            "has_figure": meta.get("has_figure", None),
            "mask_text_nonzero": meta.get("mask_text_nonzero", None),
            "mask_math_nonzero": meta.get("mask_math_nonzero", None),
            "math_line_count": meta.get("math_line_count", None),
            "equation_block_count": meta.get("equation_block_count", None),
            "table_block_count": meta.get("table_block_count", None),
            "figure_block_count": meta.get("figure_block_count", None),
            "rotation_deg": meta.get("rotation_deg", None),
            "perspective": meta.get("perspective", None),
            "book_mode": meta.get("book_mode", None),
            "text_mode": meta.get("text_mode", None),
            "text_order": meta.get("text_order", None),
            "content_bank_json": meta.get("content_bank_json", None),
            "aug_trace": meta.get("aug_trace", []),
        },
        "blocks": blocks_out,
        "lines": lines_out,
        "page_text": page_text,
        "gt_stats": ann.get("gt_stats", {}),
    }


_build_gt_export = build_gt_export



