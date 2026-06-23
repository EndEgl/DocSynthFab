# src/docsynthfab/qc/content_contracts.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple




def _content_pure_mode_from_cfg_for_qc(cfg: Any) -> str:
    """
    Detect whether content.block_mix is table-only, latex-only, text-only, or mixed.
    """
    raw_cfg = getattr(cfg, "raw", {}) or {}
    content_cfg = raw_cfg.get("content", {}) or {}
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


def _validate_content_purity_contract(
    ann: Dict[str, Any],
    cfg: Any,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Enforce pure content modes.

    If table=100, latex=100, or text=100 is requested, other block/line types
    should not leak into the generated annotation.
    """
    mode = _content_pure_mode_from_cfg_for_qc(cfg)

    if mode == "mixed":
        return True, None

    blocks = ann.get("blocks", []) or []
    lines = ann.get("lines", []) or []
    meta = ann.get("meta", {}) or {}

    block_types = [str(b.get("block_type", "")) for b in blocks]
    line_types = [str(ln.get("line_type", "")) for ln in lines]

    text_block_types = {
        "paragraph",
        "title",
        "list",
        "caption",
        "header",
        "footer",
        "text",
        "auto_paragraph_block",
    }

    if mode == "table_only":
        bad_blocks = [bt for bt in block_types if bt != "table"]
        bad_lines = [lt for lt in line_types if lt != "table_cell"]

        if bad_blocks or bad_lines:
            return False, {
                "mode": mode,
                "bad_blocks": bad_blocks[:20],
                "bad_lines": bad_lines[:20],
                "block_types": block_types[:80],
                "line_types": line_types[:80],
            }

    elif mode == "latex_only":
        bad_blocks = [bt for bt in block_types if bt != "equation"]
        bad_lines = [lt for lt in line_types if lt != "math"]

        if bad_blocks or bad_lines:
            return False, {
                "mode": mode,
                "bad_blocks": bad_blocks[:20],
                "bad_lines": bad_lines[:20],
                "block_types": block_types[:80],
                "line_types": line_types[:80],
            }

        if int(meta.get("latex_render_error_count", 0) or 0) > 0:
            return False, {
                "mode": mode,
                "reason": "latex-render-failed-in-latex-only-mode",
                "latex_render_error_count": int(meta.get("latex_render_error_count", 0) or 0),
                "latex_render_errors": meta.get("latex_render_errors", [])[:5],
            }

        if not bool(meta.get("latex_render_enabled", True)):
            return False, {
                "mode": mode,
                "reason": "latex-render-disabled-in-latex-only-mode",
            }

    elif mode == "text_only":
        bad_blocks = [bt for bt in block_types if bt not in text_block_types]
        bad_lines = [lt for lt in line_types if lt not in {"text", "caption"}]

        if bad_blocks or bad_lines:
            return False, {
                "mode": mode,
                "bad_blocks": bad_blocks[:20],
                "bad_lines": bad_lines[:20],
                "block_types": block_types[:80],
                "line_types": line_types[:80],
            }

    return True, None


def _validate_text_no_tofu_chars(
    ann: Dict[str, Any],
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Reject annotation text containing obvious tofu/replacement characters.
    """
    suspicious_chars = {
        "\uFFFD",
        "□",
        "▯",
    }

    bad_items: List[Dict[str, Any]] = []

    for ln in ann.get("lines", []) or []:
        txt = str(ln.get("gt_text", "") or "")

        if not txt:
            continue

        hits = [ch for ch in txt if ch in suspicious_chars]

        if hits:
            bad_items.append(
                {
                    "line_id": ln.get("line_id"),
                    "script": ln.get("gt_script"),
                    "hits": hits[:10],
                    "text_sample": txt[:120],
                }
            )

    if bad_items:
        return False, {
            "bad_line_count": len(bad_items),
            "items": bad_items[:20],
        }

    return True, None

_CODE_TOKEN_RE = re.compile(
    r"""
    (?:
        \b(?:cfg|bbox|mask|render|train|valid|loss|acc|model|seed|dpi)
        (?:[_:.]{1,2}[A-Za-z0-9]+)+
        (?:==|!=|<=|>=|->|::|=>|&&|\|\||\+=|-=|\*=|/=)?
    )
    |
    (?:
        \b[A-Za-z]+(?:[_:.]{1,2}[A-Za-z0-9]+)+
        (?:==|!=|<=|>=|->|::|=>|&&|\|\||\+=|-=|\*=|/=)
    )
    |
    (?:
        \b(?:cfg|bbox|mask|render|train|valid|loss|acc|model)
        (?:==|!=|<=|>=|->|::|=>|&&|\|\||\+=|-=|\*=|/=)
    )
    """,
    re.VERBOSE,
)


def _validate_text_no_code_token_leakage(
    ann: Dict[str, Any],
    max_leak_count: int = 0,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Reject synthetic code/noisy tokens leaking into natural OCR text.

    This intentionally does not reject ordinary words such as "data" alone.
    It targets generated debug-like patterns such as:
    cfg.size, bbox::seed, render__seed962, acc.mean!=, data__prob==
    """
    bad_items: List[Dict[str, Any]] = []
    total_hits = 0

    for ln in ann.get("lines", []) or []:
        txt = str(ln.get("gt_text", "") or "")

        if not txt:
            continue

        hits = [m.group(0) for m in _CODE_TOKEN_RE.finditer(txt)]

        if not hits:
            continue

        total_hits += len(hits)
        bad_items.append(
            {
                "line_id": ln.get("line_id"),
                "line_type": ln.get("line_type"),
                "script": ln.get("gt_script"),
                "hits": hits[:10],
                "text_sample": txt[:160],
            }
        )

    if total_hits > int(max_leak_count):
        return False, {
            "code_token_leak_count": int(total_hits),
            "max_code_token_leak_count": int(max_leak_count),
            "bad_line_count": len(bad_items),
            "items": bad_items[:20],
        }

    return True, None

