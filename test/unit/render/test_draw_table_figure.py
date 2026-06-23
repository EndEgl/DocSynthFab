from __future__ import annotations

import random

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from docsynthfab.render.draw_utils import (
    _draw_text_glyph_mask,
    _measure_text,
    _paste_alpha_as_binary,
    _pick_weighted,
    _sample_contrast_color,
)
from docsynthfab.render.figure_renderer import _make_random_figure_patch
from docsynthfab.render.table_renderer import _draw_table_structure


def test_pick_weighted_returns_default_for_empty_dist():
    assert _pick_weighted(random.Random(123), {}) == "latin"


def test_sample_contrast_color_ranges():
    assert all(0 <= v <= 59 for v in _sample_contrast_color(
        random.Random(1),
        {"contrast_class_dist": {"high": 1.0}},
    ))

    assert all(60 <= v <= 119 for v in _sample_contrast_color(
        random.Random(1),
        {"contrast_class_dist": {"medium": 1.0}},
    ))

    assert all(120 <= v <= 170 for v in _sample_contrast_color(
        random.Random(1),
        {"contrast_class_dist": {"low": 1.0}},
    ))


def test_measure_text_returns_positive_width():
    img = Image.new("RGB", (200, 80), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    assert _measure_text(draw, "hello", font) > 0


def test_draw_text_glyph_mask_draws_image_and_mask():
    img = Image.new("RGB", (200, 80), (255, 255, 255))
    mask = Image.new("L", (200, 80), 0)

    draw_img = ImageDraw.Draw(img)
    draw_mask = ImageDraw.Draw(mask)
    font = ImageFont.load_default()

    _draw_text_glyph_mask(
        draw_img,
        draw_mask,
        10,
        10,
        "hello",
        font,
        fill_rgb=(0, 0, 0),
    )

    assert mask.getbbox() is not None
    assert np.count_nonzero(np.array(mask)) > 0
    assert np.count_nonzero(np.array(img) != 255) > 0


def test_paste_alpha_as_binary_uses_alpha_mask():
    mask = Image.new("L", (50, 50), 0)
    alpha = Image.new("L", (10, 8), 0)
    ImageDraw.Draw(alpha).rectangle((2, 2, 8, 6), fill=255)

    _paste_alpha_as_binary(mask, alpha, 5, 7)

    arr = np.array(mask)
    assert arr[9, 7] == 255
    assert arr[0, 0] == 0


def test_make_random_figure_patch_returns_rgb_image_for_supported_families():
    for family in ["chart", "diagram", "texture", "photo", "unknown"]:
        patch = _make_random_figure_patch(
            random.Random(123),
            96,
            64,
            family,
        )

        assert patch.mode == "RGB"
        assert patch.size == (96, 64)


def test_make_random_figure_patch_handles_tiny_patch():
    patch = _make_random_figure_patch(random.Random(123), 8, 9, "chart")

    assert patch.mode == "RGB"
    assert patch.size == (8, 9)


def test_draw_table_structure_changes_pixels_for_full_grid():
    img = Image.new("RGB", (220, 160), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    _draw_table_structure(
        draw,
        20,
        20,
        200,
        140,
        rows=4,
        cols=5,
        style={
            "border_mode": "full_grid",
            "header_rows": 1,
            "header_cols": 1,
            "zebra_rows": True,
        },
        rng=random.Random(123),
    )

    arr = np.array(img)
    assert np.count_nonzero(arr != 255) > 0


def test_draw_table_structure_borderless_header_rule_is_safe():
    img = Image.new("RGB", (220, 160), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    _draw_table_structure(
        draw,
        20,
        20,
        200,
        140,
        rows=3,
        cols=4,
        style={
            "border_mode": "borderless",
            "header_rows": 1,
            "table_kind": "key_value_table",
        },
        rng=random.Random(123),
    )

    arr = np.array(img)
    assert np.count_nonzero(arr != 255) > 0