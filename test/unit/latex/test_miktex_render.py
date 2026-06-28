from __future__ import annotations

import base64
import json
import random
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from docsynthfab.latex import miktex_render as mr
import docsynthfab.latex.expression_bank as expression_bank
import docsynthfab.latex.http_render as http_render
import docsynthfab.latex.image_cleanup as image_cleanup


def _png_b64_rgba_with_ink() -> str:
    img = Image.new("RGBA", (32, 24), (255, 255, 255, 255))

    for x in range(8, 24):
        for y in range(8, 16):
            img.putpixel((x, y), (0, 0, 0, 255))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _fake_rgba_with_ink(width: int = 20, height: int = 10) -> Image.Image:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    for x in range(max(1, width // 4), max(2, width * 3 // 4)):
        for y in range(max(1, height // 4), max(2, height * 3 // 4)):
            img.putpixel((x, y), (0, 0, 0, 255))

    return img


# ======================================================================================
# normalize_latex_expr
# ======================================================================================

def test_normalize_latex_expr_allows_empty_expression_for_backward_compatibility():
    assert mr.normalize_latex_expr("") == ""


def test_normalize_latex_expr_preserves_dollar_wrappers_for_backward_compatibility():
    assert mr.normalize_latex_expr("$x+1$") == "$x+1$"


def test_normalize_latex_expr_adds_missing_frac_backslash():
    assert mr.normalize_latex_expr("frac{a}{b}") == r"\frac{a}{b}"


def test_normalize_latex_expr_does_not_break_existing_commands():
    expr = mr.normalize_latex_expr(r"\frac{a}{b}+\sqrt{x}+\alpha")

    assert expr == r"\frac{a}{b}+\sqrt{x}+\alpha"


def test_normalize_latex_expr_returns_string_for_plain_text():
    expr = mr.normalize_latex_expr("x + y")

    assert isinstance(expr, str)
    assert expr == "x + y"


# ======================================================================================
# image_cleanup.py
# ======================================================================================

def test_crop_rgba_to_alpha_bbox_extracts_ink_from_white_background():
    img = Image.new("RGBA", (80, 40), (255, 255, 255, 255))

    for x in range(20, 60):
        for y in range(12, 28):
            img.putpixel((x, y), (0, 0, 0, 255))

    out = image_cleanup.crop_rgba_to_alpha_bbox(img, pad=2)

    assert out.mode == "RGBA"
    assert out.width < img.width
    assert out.height < img.height
    assert out.getchannel("A").getbbox() is not None


def test_crop_rgba_to_alpha_bbox_raises_on_empty_ink():
    img = Image.new("RGBA", (80, 40), (255, 255, 255, 255))

    with pytest.raises(mr.LatexRenderError, match="render/latex-empty-ink"):
        image_cleanup.crop_rgba_to_alpha_bbox(img)


# ======================================================================================
# miktex_render.py public wrapper
# ======================================================================================

def test_render_latex_to_rgba_rejects_unsupported_backend():
    with pytest.raises(mr.LatexRenderError, match="render/latex-unsupported-backend"):
        mr.render_latex_to_rgba("x+1", backend="local")


def test_render_latex_to_rgba_delegates_to_http_backend(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_http_render(latex_expr: str, **kwargs: Any) -> Image.Image:
        calls.append((latex_expr, kwargs))
        return _fake_rgba_with_ink()

    monkeypatch.setattr(mr, "render_latex_to_rgba_http", fake_http_render)

    img = mr.render_latex_to_rgba(
        "x+1",
        backend="http",
        http_base_url="http://fake",
        timeout_s=7,
        raster_dpi=144,
    )

    assert img.mode == "RGBA"
    assert calls[0][0] == "x+1"
    assert calls[0][1]["http_base_url"] == "http://fake"
    assert calls[0][1]["timeout_s"] == 7
    assert calls[0][1]["raster_dpi"] == 144


# ======================================================================================
# http_render.py
# ======================================================================================

def _disable_http_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI1_LATEX_CLIENT_LOCK", "0")
    monkeypatch.setattr(
        http_render,
        "ensure_http_renderer_ready_once",
        lambda http_base_url: None,
    )


def test_render_latex_to_rgba_http_success(monkeypatch: pytest.MonkeyPatch):
    _disable_http_runtime(monkeypatch)

    class Resp:
        status_code = 200
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "ok": True,
                "png_base64": _png_b64_rgba_with_ink(),
            }

    def fake_post(url, json, timeout):
        assert url == "http://fake/render"
        assert json["expr"] == r"\frac{a}{b}"
        assert json["dpi"] == 120
        return Resp()

    monkeypatch.setattr(http_render.requests, "post", fake_post)

    img = http_render.render_latex_to_rgba_http(
        "frac{a}{b}",
        http_base_url="http://fake",
        timeout_s=1,
        raster_dpi=120,
    )

    assert img.mode == "RGBA"
    assert img.getchannel("A").getbbox() is not None


def test_render_latex_to_rgba_http_raises_on_unreachable(
    monkeypatch: pytest.MonkeyPatch,
):
    _disable_http_runtime(monkeypatch)

    def fake_post(url, json, timeout):
        raise http_render.requests.RequestException("network down")

    monkeypatch.setattr(http_render.requests, "post", fake_post)

    with pytest.raises(mr.LatexRenderError, match="render/latex-http-unreachable"):
        http_render.render_latex_to_rgba_http("x", http_base_url="http://fake")


def test_render_latex_to_rgba_http_raises_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
):
    _disable_http_runtime(monkeypatch)

    def fake_post(url, json, timeout):
        raise http_render.requests.Timeout("timeout")

    monkeypatch.setattr(http_render.requests, "post", fake_post)

    with pytest.raises(mr.LatexRenderError, match="render/latex-http-timeout"):
        http_render.render_latex_to_rgba_http("x", http_base_url="http://fake")


def test_render_latex_to_rgba_http_raises_on_renderer_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    _disable_http_runtime(monkeypatch)

    class Resp:
        status_code = 200
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "ok": False,
                "error": "compile failed",
                "stdout": "STDOUT",
                "stderr": "STDERR",
            }

    monkeypatch.setattr(http_render.requests, "post", lambda *a, **k: Resp())

    with pytest.raises(mr.LatexRenderError, match="render/latex-http-failed"):
        http_render.render_latex_to_rgba_http("x", http_base_url="http://fake")


def test_render_latex_to_rgba_http_raises_on_missing_png(
    monkeypatch: pytest.MonkeyPatch,
):
    _disable_http_runtime(monkeypatch)

    class Resp:
        status_code = 200
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "ok": True,
            }

    monkeypatch.setattr(http_render.requests, "post", lambda *a, **k: Resp())

    with pytest.raises(mr.LatexRenderError, match="render/latex-http-empty-response"):
        http_render.render_latex_to_rgba_http("x", http_base_url="http://fake")


def test_ensure_http_renderer_ready_calls_docker_when_auto_docker_enabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AI1_LATEX_AUTO_DOCKER", "1")

    calls = []

    monkeypatch.setattr(
        http_render,
        "ensure_latex_container",
        lambda **kwargs: calls.append(kwargs),
    )

    http_render.ensure_http_renderer_ready(http_base_url="http://fake")

    assert calls
    assert calls[0]["http_base_url"] == "http://fake"
    assert calls[0]["build_if_missing"] is False
    assert calls[0]["force_recreate_if_unhealthy"] is False
    assert calls[0]["create_if_missing"] is False


def test_ensure_http_renderer_ready_skips_docker_when_auto_docker_disabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AI1_LATEX_AUTO_DOCKER", "0")

    def should_not_call(**kwargs):
        raise AssertionError("ensure_latex_container should not be called")

    monkeypatch.setattr(http_render, "ensure_latex_container", should_not_call)

    http_render.ensure_http_renderer_ready(http_base_url="http://fake")


def test_check_latex_http_health_returns_none_when_health_ok(
    monkeypatch: pytest.MonkeyPatch,
):
    class Resp:
        status_code = 200
        text = ""

        def json(self):
            return {"ok": True}

    def fake_get(url, timeout):
        assert url in {"http://fake/health", "http://fake/healthz"}
        return Resp()

    monkeypatch.setattr(http_render.requests, "get", fake_get)

    assert http_render.check_latex_http_health("http://fake", timeout_s=1) is None


def test_check_latex_http_health_raises_on_error(monkeypatch: pytest.MonkeyPatch):
    def fake_get(url, timeout):
        raise RuntimeError("down")

    monkeypatch.setattr(http_render.requests, "get", fake_get)

    with pytest.raises(mr.LatexRenderError, match="render/latex-http-health-failed"):
        http_render.check_latex_http_health("http://fake", timeout_s=1)


# ======================================================================================
# expression generation / math bank
# ======================================================================================

def test_sample_latex_expr_returns_non_empty_expression():
    expr = mr.sample_latex_expr(random.Random(123), level="medium")

    assert isinstance(expr, str)
    assert expr.strip()


def test_sample_latex_expr_respects_allowed_ops_for_simple_algebra():
    expr = mr.sample_latex_expr(
        random.Random(123),
        level="clean",
        allowed_ops=["add_sub"],
    )

    assert isinstance(expr, str)
    assert expr.strip()


def test_generate_math_bank_writes_pngs_and_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def fake_render(expr: str, **kwargs: Any) -> Image.Image:
        return _fake_rgba_with_ink(20, 10)

    monkeypatch.setattr(mr, "render_latex_to_rgba", fake_render)
    monkeypatch.setattr(
        expression_bank,
        "sample_latex_expr",
        lambda rng, **kwargs: f"x+{rng.randint(1, 999)}",
    )

    samples = mr.generate_math_bank(
        out_dir=tmp_path,
        count=3,
        seed=123,
        timeout_s=1,
        raster_dpi=120,
        unique=True,
        backend="http",
        http_base_url="http://fake",
    )

    assert len(samples) == 3

    for sample in samples:
        assert Path(sample.png_path).exists()
        assert sample.w == 20
        assert sample.h == 10

    meta_path = tmp_path / "math_bank.json"
    assert meta_path.exists()

    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    assert meta["count"] == 3
    assert meta["backend"] == "http"
    assert len(meta["items"]) == 3


def test_generate_math_bank_rejects_unsupported_backend(tmp_path: Path):
    with pytest.raises(mr.LatexRenderError, match="render/latex-unsupported-backend"):
        mr.generate_math_bank(
            out_dir=tmp_path,
            count=1,
            backend="local",
        )


def test_generate_math_bank_stops_at_max_tries_when_unique_exhausted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(expression_bank, "sample_latex_expr", lambda *a, **k: "x+1")
    monkeypatch.setattr(mr, "render_latex_to_rgba", lambda *a, **k: _fake_rgba_with_ink(10, 5))

    samples = mr.generate_math_bank(
        out_dir=tmp_path,
        count=5,
        unique=True,
        max_tries=3,
        backend="http",
        http_base_url="http://fake",
    )

    assert len(samples) == 1

    meta = json.loads((tmp_path / "math_bank.json").read_text(encoding="utf-8"))

    assert meta["count"] == 1
    assert meta["tries"] == 3
    assert meta["duplicate_skips"] == 2