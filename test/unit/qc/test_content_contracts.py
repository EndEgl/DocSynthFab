from __future__ import annotations

from typing import Any

from docsynthfab.qc.content_contracts import (
    _content_pure_mode_from_cfg_for_qc,
    _validate_content_purity_contract,
    _validate_text_no_code_token_leakage,
    _validate_text_no_tofu_chars,
)


class Cfg:
    def __init__(self, block_mix: dict[str, Any]):
        self.raw = {
            "content": {
                "block_mix": block_mix,
            }
        }


def test_content_pure_mode_detection():
    assert _content_pure_mode_from_cfg_for_qc(Cfg({"text": 100, "table": 0, "latex": 0})) == "text_only"
    assert _content_pure_mode_from_cfg_for_qc(Cfg({"text": 0, "table": 100, "latex": 0})) == "table_only"
    assert _content_pure_mode_from_cfg_for_qc(Cfg({"text": 0, "table": 0, "latex": 100})) == "latex_only"
    assert _content_pure_mode_from_cfg_for_qc(Cfg({"text": 50, "table": 50, "latex": 0})) == "mixed"
    assert _content_pure_mode_from_cfg_for_qc(Cfg({})) == "mixed"


def test_table_only_contract_rejects_non_table_blocks_and_lines():
    ann = {
        "meta": {},
        "blocks": [
            {"block_type": "table"},
            {"block_type": "paragraph"},
        ],
        "lines": [
            {"line_type": "table_cell"},
            {"line_type": "text"},
        ],
    }

    ok, extra = _validate_content_purity_contract(
        ann,
        Cfg({"text": 0, "table": 100, "latex": 0}),
    )

    assert ok is False
    assert "paragraph" in extra["bad_blocks"]
    assert "text" in extra["bad_lines"]


def test_latex_only_contract_rejects_render_error_even_when_blocks_are_equations():
    ann = {
        "meta": {
            "latex_render_error_count": 1,
            "latex_render_errors": [{"error": "render failed"}],
            "latex_render_enabled": True,
        },
        "blocks": [
            {"block_type": "equation"},
        ],
        "lines": [
            {"line_type": "math"},
        ],
    }

    ok, extra = _validate_content_purity_contract(
        ann,
        Cfg({"text": 0, "table": 0, "latex": 100}),
    )

    assert ok is False
    assert extra["reason"] == "latex-render-failed-in-latex-only-mode"


def test_latex_only_contract_rejects_disabled_renderer():
    ann = {
        "meta": {
            "latex_render_error_count": 0,
            "latex_render_enabled": False,
        },
        "blocks": [
            {"block_type": "equation"},
        ],
        "lines": [
            {"line_type": "math"},
        ],
    }

    ok, extra = _validate_content_purity_contract(
        ann,
        Cfg({"text": 0, "table": 0, "latex": 100}),
    )

    assert ok is False
    assert extra["reason"] == "latex-render-disabled-in-latex-only-mode"


def test_text_only_contract_allows_text_like_blocks():
    ann = {
        "meta": {},
        "blocks": [
            {"block_type": "title"},
            {"block_type": "paragraph"},
            {"block_type": "list"},
            {"block_type": "caption"},
        ],
        "lines": [
            {"line_type": "text"},
            {"line_type": "caption"},
        ],
    }

    ok, extra = _validate_content_purity_contract(
        ann,
        Cfg({"text": 100, "table": 0, "latex": 0}),
    )

    assert ok is True
    assert extra is None


def test_text_no_tofu_chars_rejects_replacement_symbols():
    ann = {
        "lines": [
            {"line_id": 1, "gt_text": "bad □ text", "gt_script": "latin"},
            {"line_id": 2, "gt_text": "bad \uFFFD text", "gt_script": "latin"},
        ]
    }

    ok, extra = _validate_text_no_tofu_chars(ann)

    assert ok is False
    assert extra["bad_line_count"] == 2


def test_text_no_tofu_chars_accepts_clean_text():
    ann = {
        "lines": [
            {"line_id": 1, "gt_text": "İstanbul ölçü deneme", "gt_script": "latin_tr"},
        ]
    }

    ok, extra = _validate_text_no_tofu_chars(ann)

    assert ok is True
    assert extra is None


def test_code_token_leakage_rejects_debug_like_tokens():
    ann = {
        "lines": [
            {
                "line_id": 1,
                "line_type": "text",
                "gt_script": "latin",
                "gt_text": "This leaked cfg.size and bbox::seed into text.",
            }
        ]
    }

    ok, extra = _validate_text_no_code_token_leakage(ann, max_leak_count=0)

    assert ok is False
    assert extra["code_token_leak_count"] >= 2
    assert extra["bad_line_count"] == 1


def test_code_token_leakage_allows_ordinary_text():
    ann = {
        "lines": [
            {
                "line_id": 1,
                "line_type": "text",
                "gt_script": "latin",
                "gt_text": "ordinary data table report text",
            }
        ]
    }

    ok, extra = _validate_text_no_code_token_leakage(ann, max_leak_count=0)

    assert ok is True
    assert extra is None