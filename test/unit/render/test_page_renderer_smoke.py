from __future__ import annotations

import random
from typing import Any

import numpy as np
import pytest

import docsynthfab.render.page_renderer as pr
from docsynthfab.layout.specs import BlockSpec, LineSpec, PageSpec


class DummyCfg:
    def __init__(self) -> None:
        self.raw = {
            "page": {
                "bg_color_rgb": [255, 255, 255],
            },
            "content": {
                "block_mix": {
                    "text": 100,
                    "table": 0,
                    "latex": 0,
                },
                "text_mode": "words",
                "text_order": "random",
            },
            "render": {
                "text": {
                    "safe_ocr_line_guard": False,
                    "max_text_generation_attempts": 1,
                    "font_size": {
                        "distribution": "uniform",
                        "min_px": 10,
                        "max_px": 12,
                    },
                },
                "non_text": {
                    "enable": False,
                    "watermark_prob": 0.0,
                },
                "latex": {
                    "enable": False,
                    "health_check": False,
                    "draw_fallback_expr": False,
                },
            },
            "style": {},
        }

    def render(self) -> dict[str, Any]:
        return self.raw["render"]


class DummyTextProvider:
    @classmethod
    def from_json(cls, *args, **kwargs):
        return cls()

    def next_text(self, *args, **kwargs):
        return "provider text"


def _text_page_spec() -> PageSpec:
    return PageSpec(
        page_id="000001",
        w=240,
        h=140,
        dpi=300,
        page_size_name="unit",
        page_width_in=1.0,
        page_height_in=1.0,
        orientation="portrait",
        page_family="report",
        layout_type="single_col",
        density_level="normal",
        scale_profile="dpi300",
        noise_level="clean",
        rotation_deg=0.0,
        perspective=False,
        has_table=False,
        has_equation=False,
        has_figure=False,
        blocks=[
            BlockSpec(
                block_id=0,
                block_type="paragraph",
                block_order=0,
                column_id=0,
                bbox=(20, 20, 180, 70),
                style={},
            ),
        ],
        lines=[
            LineSpec(
                line_id=0,
                block_id=0,
                line_type="text",
                line_order_in_block=0,
                global_line_order=0,
                bbox=(25, 30, 150, 18),
            ),
        ],
    )


def test_render_page_layers_text_smoke(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        pr,
        "ensure_content_bank",
        lambda cfg: {"generated_json": "unit-content-bank.json"},
    )
    monkeypatch.setattr(pr, "TextProvider", DummyTextProvider)
    monkeypatch.setattr(pr, "_choose_script_for_line", lambda *a, **k: "latin")
    monkeypatch.setattr(pr, "_make_line_text", lambda *a, **k: ("hello world", "latin"))

    out = pr.render_page_layers(
        _text_page_spec(),
        DummyCfg(),
        random.Random(123),
    )

    assert set(out) == {"image_u8", "mask_text_u8", "mask_math_u8", "ann"}

    image = out["image_u8"]
    mask_text = out["mask_text_u8"]
    mask_math = out["mask_math_u8"]
    ann = out["ann"]

    assert image.shape == (140, 240, 3)
    assert image.dtype == np.uint8

    assert mask_text.shape == (140, 240)
    assert mask_text.dtype == np.uint8
    assert set(np.unique(mask_text)).issubset({0, 255})
    assert np.count_nonzero(mask_text) > 0

    assert mask_math.shape == (140, 240)
    assert mask_math.dtype == np.uint8
    assert set(np.unique(mask_math)).issubset({0, 255})
    assert np.count_nonzero(mask_math) == 0

    assert ann["page_id"] == "000001"
    assert ann["size"]["w"] == 240
    assert ann["size"]["h"] == 140
    assert ann["meta"]["content_pure_mode"] == "text_only"
    assert ann["meta"]["has_table"] is False
    assert ann["meta"]["has_equation"] is False
    assert ann["meta"]["has_figure"] is False

    assert ann["lines"][0]["gt_text"] == "hello world"
    assert ann["lines"][0]["gt_script"] == "latin"
    assert ann["gt_page_text"] == "hello world"
    assert ann["gt_stats"]["has_gt_text_lines"] == 1
    assert ann["gt_stats"]["has_gt_math_lines"] == 0