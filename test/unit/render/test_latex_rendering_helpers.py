from __future__ import annotations

import random

import pytest
from PIL import Image, ImageDraw, ImageFont

import docsynthfab.render.latex_rendering as lr


def _rgba_with_ink(w: int = 20, h: int = 10) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((2, 2, w - 3, h - 3), fill=(0, 0, 0, 255))
    return img


def test_fit_rgba_contain_returns_target_size_and_preserves_alpha():
    out = lr._fit_rgba_contain(
        _rgba_with_ink(20, 10),
        100,
        40,
    )

    assert out.mode == "RGBA"
    assert out.size == (100, 40)
    assert out.getchannel("A").getbbox() is not None


def test_fit_rgba_contain_handles_empty_source_size_safely():
    out = lr._fit_rgba_contain(
        Image.new("RGBA", (1, 1), (0, 0, 0, 0)),
        0,
        0,
    )

    assert out.mode == "RGBA"
    assert out.size == (1, 1)


def test_resolve_latex_cfg_defaults_and_forces_http_backend():
    out = lr._resolve_latex_cfg(
        {
            "latex": {
                "enable": True,
                "backend": "local",
                "timeout_s": 7,
                "raster_dpi": 200,
                "level": "HARD",
            }
        }
    )

    assert out["enable"] is True
    assert out["backend"] == "http"
    assert out["timeout_s"] == 7
    assert out["raster_dpi"] == 200
    assert out["level"] == "hard"
    assert out["http_base_url"] == "http://127.0.0.1:8080"


def test_render_latex_with_retries_success(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_render(expr, **kwargs):
        calls.append((expr, kwargs))
        return _rgba_with_ink(20, 10)

    monkeypatch.setattr(lr, "render_latex_to_rgba", fake_render)
    monkeypatch.setattr(lr, "sample_latex_expr", lambda *a, **k: r"x+y=1")

    ok, expr, img, errors = lr._render_latex_with_retries(
        initial_expr=r"x^2+y^2=z^2",
        rng=random.Random(123),
        latex_level="easy",
        allowed_ops=None,
        pdflatex_cmd="pdflatex",
        timeout_s=3,
        raster_dpi=200,
        latex_backend="http",
        latex_http_base_url="http://unit",
        target_w=80,
        target_h=32,
        random_offset=False,
    )

    assert ok is True
    assert expr
    assert img is not None
    assert img.size == (80, 32)
    assert errors == []
    assert calls


def test_render_latex_with_retries_collects_errors_on_failure(monkeypatch: pytest.MonkeyPatch):
    def fake_render(*args, **kwargs):
        raise RuntimeError("renderer down")

    monkeypatch.setattr(lr, "render_latex_to_rgba", fake_render)
    monkeypatch.setattr(lr, "sample_latex_expr", lambda *a, **k: r"a+b")

    ok, expr, img, errors = lr._render_latex_with_retries(
        initial_expr=r"x+y=0",
        rng=random.Random(123),
        latex_level="easy",
        allowed_ops=None,
        pdflatex_cmd="pdflatex",
        timeout_s=3,
        raster_dpi=200,
        latex_backend="http",
        latex_http_base_url="http://unit",
        target_w=80,
        target_h=32,
        random_offset=False,
    )

    assert ok is False
    assert expr
    assert img is None
    assert errors
    assert any(item["stage"] == "render_retry" for item in errors)


def test_draw_math_fallback_text_draws_mask(monkeypatch: pytest.MonkeyPatch):
    class FakeRng(random.Random):
        def choice(self, seq):
            return "x"

    monkeypatch.setattr(
        lr,
        "_fit_font_to_bbox_height",
        lambda *a, **k: ImageFont.load_default(),
    )
    monkeypatch.setattr(
        lr,
        "_sample_contrast_color",
        lambda *a, **k: (0, 0, 0),
    )

    img = Image.new("RGB", (120, 60), (255, 255, 255))
    mask = Image.new("L", (120, 60), 0)

    lr._draw_math_fallback_text(
        ImageDraw.Draw(img),
        ImageDraw.Draw(mask),
        x=10,
        y=10,
        ww=80,
        hh=30,
        expr=r"x+y=0",
        fonts_dir=None,
        base_size=12,
        rng=FakeRng(123),
        style_cfg={},
    )

    assert mask.getbbox() is not None