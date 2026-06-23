# test/unit/latex/test_latex_http_backend_contract.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - requests>=2.31,<3.0

from __future__ import annotations

import pytest

from docsynthfab.latex.errors import LatexRenderError


def test_latex_http_renderer_rejects_non_renderer_response(monkeypatch):
    import docsynthfab.latex.http_render as http_render

    class FakeResponse:
        status_code = 200
        text = "<html>NiceGUI page</html>"

        def json(self):
            raise ValueError("not json")

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(http_render.requests, "get", fake_get)

    with pytest.raises(LatexRenderError) as exc:
        http_render.check_latex_http_health("http://127.0.0.1:8080", timeout_s=1)

    assert "latex" in str(exc.value).lower() or "health" in str(exc.value).lower()


def test_latex_http_renderer_health_timeout_is_fast(monkeypatch):
    import requests
    import docsynthfab.latex.http_render as http_render

    def fake_get(*args, **kwargs):
        raise requests.Timeout("synthetic timeout")

    monkeypatch.setattr(http_render.requests, "get", fake_get)

    with pytest.raises(LatexRenderError) as exc:
        http_render.check_latex_http_health("http://127.0.0.1:8080", timeout_s=1)

    assert "timeout" in str(exc.value).lower() or "unreachable" in str(exc.value).lower()



