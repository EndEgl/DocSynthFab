from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from docsynthfab.render.page_renderer import (
    _box_overlap_ratio_min_area,
    _dominant_script_family,
    _has_excessive_text_overlap,
    _has_unsafe_ocr_text_noise,
    _has_unsafe_script_mix,
    _rendered_text_bbox_xywh,
    _safe_ocr_fallback_text,
    _script_families_in_text,
    _script_family_for_char,
)


def test_script_family_for_char_detects_major_scripts():
    assert _script_family_for_char("A") == "latin"
    assert _script_family_for_char("ğ") == "latin"
    assert _script_family_for_char("Ω") == "el"
    assert _script_family_for_char("Ж") == "ru"
    assert _script_family_for_char("א") == "he"
    assert _script_family_for_char("ش") == "ar"
    assert _script_family_for_char("中") == "zh"
    assert _script_family_for_char("あ") == "ja"
    assert _script_family_for_char("한") == "ko"
    assert _script_family_for_char("ก") == "th"


def test_script_families_and_dominant_script():
    families = _script_families_in_text("hello ЖЖЖ")

    assert families["latin"] == 5
    assert families["ru"] == 3
    assert _dominant_script_family("hello", fallback="ru") == "latin"
    assert _dominant_script_family("ЖЖЖЖЖЖ hello", fallback="latin") == "ru"
    assert _dominant_script_family("123", fallback="latin") == "latin"


def test_unsafe_script_mix_detects_strong_mixed_scripts():
    assert _has_unsafe_script_mix("hello Привет") is True
    assert _has_unsafe_script_mix("hello world") is False
    assert _has_unsafe_script_mix("12345") is False


def test_unsafe_ocr_text_noise_detects_code_and_symbol_noise():
    assert _has_unsafe_ocr_text_noise("") is True
    assert _has_unsafe_ocr_text_noise("bad bbox::seed token") is True
    assert _has_unsafe_ocr_text_noise("bad □ text") is True
    assert _has_unsafe_ocr_text_noise("normal document reference") is False


def test_safe_ocr_fallback_text_returns_non_empty_language_samples():
    assert _safe_ocr_fallback_text("latin", "text", 0)
    assert "örnek" in _safe_ocr_fallback_text("tr", "text", 0)
    assert _safe_ocr_fallback_text("unknown", "text", 0) == "example data line"


def test_box_overlap_ratio_min_area_contract():
    assert _box_overlap_ratio_min_area((0, 0, 10, 10), (20, 20, 10, 10)) == 0.0
    assert _box_overlap_ratio_min_area((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0

    partial = _box_overlap_ratio_min_area((0, 0, 10, 10), (5, 0, 10, 10))
    assert 0.0 < partial < 1.0


def test_has_excessive_text_overlap_uses_min_area_ratio():
    obstacles = [(0, 0, 10, 10)]

    assert _has_excessive_text_overlap((1, 1, 10, 10), obstacles, max_ratio=0.05) is True
    assert _has_excessive_text_overlap((30, 30, 10, 10), obstacles, max_ratio=0.05) is False


def test_rendered_text_bbox_xywh_is_inside_page():
    img = Image.new("RGB", (200, 100), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    bbox = _rendered_text_bbox_xywh(
        draw,
        x=10,
        y=10,
        text="hello",
        font=font,
        page_w=200,
        page_h=100,
    )

    x, y, w, h = bbox

    assert w >= 4
    assert h >= 4
    assert 0 <= x < 200
    assert 0 <= y < 100
    assert x + w <= 200
    assert y + h <= 100