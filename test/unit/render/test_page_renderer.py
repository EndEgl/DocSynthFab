from __future__ import annotations

from docsynthfab.render.page_renderer import _content_pure_mode_from_cfg


def test_content_pure_mode_detects_table_only():
    assert _content_pure_mode_from_cfg(
        {"block_mix": {"text": 0, "table": 100, "latex": 0}}
    ) == "table_only"


def test_content_pure_mode_detects_latex_only():
    assert _content_pure_mode_from_cfg(
        {"block_mix": {"text": 0, "table": 0, "latex": 100}}
    ) == "latex_only"


def test_content_pure_mode_detects_text_only():
    assert _content_pure_mode_from_cfg(
        {"block_mix": {"text": 100, "table": 0, "latex": 0}}
    ) == "text_only"


def test_content_pure_mode_detects_mixed():
    assert _content_pure_mode_from_cfg(
        {"block_mix": {"text": 60, "table": 25, "latex": 15}}
    ) == "mixed"


def test_content_pure_mode_zero_total_is_mixed():
    assert _content_pure_mode_from_cfg(
        {"block_mix": {"text": 0, "table": 0, "latex": 0}}
    ) == "mixed"


def test_content_pure_mode_missing_block_mix_is_mixed():
    assert _content_pure_mode_from_cfg({}) == "mixed"



