from __future__ import annotations

import base64
import json
import random
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from ai1_gen.latex import miktex_render as mr


def _png_b64_rgba_with_ink() -> str:
    img = Image.new("RGBA", (32, 24), (255, 255, 255, 255))
    for x in range(8, 24):
        for y in range(8, 16):
            img.putpixel((x, y), (0, 0, 0, 255))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ======================================================================================
# normalize_latex_expr
# ======================================================================================

def test_normalize_latex_expr_rejects_empty_expression():
    with pytest.raises(mr.LatexRenderError, match="render/latex-empty-expr"):
        mr.normalize_latex_expr("")


def test_normalize_latex_expr_strips_dollar_wrappers():
    assert mr.normalize_latex_expr("$x+1$") == "x+1"


def test_normalize_latex_expr_adds_missing_latex_command_backslashes():
    expr = mr.normalize_latex_expr("frac{a}{b} + sqrt{x} + lambda")

    assert r"\frac{a}{b}" in expr
    assert r"\sqrt{x}" in expr
    assert r"\lambda" in expr


def test_normalize_latex_expr_does_not_break_existing_commands():
    expr = mr.normalize_latex_expr(r"\frac{a}{b}+\sqrt{x}+\alpha")

    assert expr == r"\frac{a}{b}+\sqrt{x}+\alpha"


def test_normalize_latex_expr_simplifies_double_escaped_known_commands():
    expr = mr.normalize_latex_expr(r"\\frac{a}{b}+\\sqrt{x}")

    assert expr == r"\frac{a}{b}+\sqrt{x}"


# ======================================================================================
# image crop / cleanup
# ======================================================================================

def test_crop_rgba_to_alpha_bbox_extracts_ink_from_white_background():
    img = Image.new("RGBA", (80, 40), (255, 255, 255, 255))
    for x in range(20, 60):
        for y in range(12, 28):
            img.putpixel((x, y), (0, 0, 0, 255))

    out = mr._crop_rgba_to_alpha_bbox(img, pad=2)

    assert out.mode == "RGBA"
    assert out.width < img.width
    assert out.height < img.height
    assert out.getchannel("A").getbbox() is not None


def test_crop_rgba_to_alpha_bbox_raises_on_empty_ink():
    img = Image.new("RGBA", (80, 40), (255, 255, 255, 255))

    with pytest.raises(mr.LatexRenderError, match="render/latex-empty-ink"):
        mr._crop_rgba_to_alpha_bbox(img)


# ======================================================================================
# HTTP rendering
# ======================================================================================

def test_render_latex_to_rgba_rejects_unsupported_backend():
    with pytest.raises(mr.LatexRenderError, match="render/latex-unsupported-backend"):
        mr.render_latex_to_rgba("x+1", backend="local")


def test_render_latex_to_rgba_http_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI1_LATEX_AUTO_DOCKER", "0")

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "ok": True,
                "png_base64": _png_b64_rgba_with_ink(),
            }

    class Requests:
        @staticmethod
        def post(url, json, timeout):
            assert url == "http://fake/render"
            assert json["expr"] == r"\frac{a}{b}"
            return Resp()

    monkeypatch.setitem(__import__("sys").modules, "requests", Requests)

    img = mr._render_latex_to_rgba_http(
        "frac{a}{b}",
        http_base_url="http://fake",
        timeout_s=1,
        raster_dpi=120,
    )

    assert img.mode == "RGBA"
    assert img.getchannel("A").getbbox() is not None


def test_render_latex_to_rgba_http_raises_when_requests_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AI1_LATEX_AUTO_DOCKER", "0")
    monkeypatch.setitem(__import__("sys").modules, "requests", None)

    with pytest.raises(mr.LatexRenderError, match="render/latex-http-missing"):
        mr._render_latex_to_rgba_http("x", http_base_url="http://fake")


def test_render_latex_to_rgba_http_raises_on_unreachable(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AI1_LATEX_AUTO_DOCKER", "0")

    class Requests:
        @staticmethod
        def post(url, json, timeout):
            raise RuntimeError("network down")

    monkeypatch.setitem(__import__("sys").modules, "requests", Requests)

    with pytest.raises(mr.LatexRenderError, match="render/latex-http-unreachable"):
        mr._render_latex_to_rgba_http("x", http_base_url="http://fake")


def test_render_latex_to_rgba_http_raises_on_renderer_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AI1_LATEX_AUTO_DOCKER", "0")

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "ok": False,
                "error": "compile failed",
                "stdout": "STDOUT",
                "stderr": "STDERR",
            }

    class Requests:
        @staticmethod
        def post(url, json, timeout):
            return Resp()

    monkeypatch.setitem(__import__("sys").modules, "requests", Requests)

    with pytest.raises(mr.LatexRenderError, match="render/latex-http-failed"):
        mr._render_latex_to_rgba_http("x", http_base_url="http://fake")


def test_render_latex_to_rgba_http_raises_on_missing_png(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AI1_LATEX_AUTO_DOCKER", "0")

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "ok": True,
            }

    class Requests:
        @staticmethod
        def post(url, json, timeout):
            return Resp()

    monkeypatch.setitem(__import__("sys").modules, "requests", Requests)

    with pytest.raises(mr.LatexRenderError, match="render/latex-http-empty-response"):
        mr._render_latex_to_rgba_http("x", http_base_url="http://fake")


def test_render_latex_to_rgba_http_auto_docker_calls_ensure_container(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AI1_LATEX_AUTO_DOCKER", "1")
    calls = []

    monkeypatch.setattr(
        mr,
        "ensure_latex_container",
        lambda **kwargs: calls.append(kwargs),
    )

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "ok": True,
                "png_base64": _png_b64_rgba_with_ink(),
            }

    class Requests:
        @staticmethod
        def post(url, json, timeout):
            return Resp()

    monkeypatch.setitem(__import__("sys").modules, "requests", Requests)

    img = mr._render_latex_to_rgba_http("x", http_base_url="http://fake")

    assert img.mode == "RGBA"
    assert calls
    assert calls[0]["http_base_url"] == "http://fake"


def test_check_latex_http_health_true_when_health_ok(monkeypatch: pytest.MonkeyPatch):
    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class Requests:
        @staticmethod
        def get(url, timeout):
            assert url == "http://fake/health"
            return Resp()

    monkeypatch.setitem(__import__("sys").modules, "requests", Requests)

    assert mr.check_latex_http_health(http_base_url="http://fake") is True


def test_check_latex_http_health_false_on_error(monkeypatch: pytest.MonkeyPatch):
    class Requests:
        @staticmethod
        def get(url, timeout):
            raise RuntimeError("down")

    monkeypatch.setitem(__import__("sys").modules, "requests", Requests)

    assert mr.check_latex_http_health(http_base_url="http://fake") is False


# ======================================================================================
# expression generation
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
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    def fake_render(expr: str, **kwargs: Any) -> Image.Image:
        img = Image.new("RGBA", (20, 10), (0, 0, 0, 0))
        for x in range(5, 15):
            for y in range(3, 7):
                img.putpixel((x, y), (0, 0, 0, 255))
        return img

    monkeypatch.setattr(mr, "render_latex_to_rgba", fake_render)
    monkeypatch.setattr(mr, "sample_latex_expr", lambda rng, **kwargs: f"x+{rng.randint(1, 999)}")

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


def test_generate_math_bank_rejects_unsupported_backend(tmp_path):
    with pytest.raises(mr.LatexRenderError, match="render/latex-unsupported-backend"):
        mr.generate_math_bank(
            out_dir=tmp_path,
            count=1,
            backend="local",
        )


def test_generate_math_bank_stops_at_max_tries_when_unique_exhausted(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(mr, "sample_latex_expr", lambda *args, **kwargs: "x+1")

    def fake_render(expr: str, **kwargs: Any) -> Image.Image:
        return Image.new("RGBA", (10, 5), (0, 0, 0, 255))

    monkeypatch.setattr(mr, "render_latex_to_rgba", fake_render)

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