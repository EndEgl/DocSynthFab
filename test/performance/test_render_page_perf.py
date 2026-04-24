from __future__ import annotations

import time

from ai1_gen.cli import _make_fallback_render


class CfgStub:
    raw = {"page": {"bg_color_rgb": [255, 255, 255]}}
    version = "ai1-ds-v1.3.2"


def test_render_page_perf_smoke():
    cfg = CfgStub()

    t0 = time.perf_counter()
    for i in range(10):
        _make_fallback_render(cfg, page_id=f"{i:06d}", dpi=300)
    elapsed = time.perf_counter() - t0

    assert elapsed < 5.0