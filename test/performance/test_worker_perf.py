from __future__ import annotations

import numpy as np
import time

import docsynthfab.cli as cli_mod


class CfgStub:
    def __init__(self) -> None:
        self.raw = {"page": {"bg_color_rgb": [255, 255, 255]}}

    def augment(self):
        return {"enable": False}

    version = "docsynthfab-ds-v0.1"


def test_worker_perf_smoke(tmp_path, monkeypatch):
    cfg = CfgStub()

    def fake_load_config(_path):
        return cfg

    def fake_sample_page_spec(_cfg, _rng, _idx, page_id):
        return {"page_id": page_id}

    def fake_render_page_layers(_ps, _cfg, _rng):
        ann = {
            "version": "docsynthfab-ds-v0.1",
            "page_id": "000001",
            "size": {"w": 128, "h": 64, "dpi": 300},
            "meta": {
                "density_level": "normal",
                "scale_profile": "dpi300",
                "noise_level": "clean",
                "page_family": "report",
                "has_table": False,
                "has_equation": False,
                "has_equation_layout": False,
                "has_figure": False,
            },
            "gt_page_text": "worker-perf",
            "lines": [
                {
                    "line_id": 0,
                    "block_id": 0,
                    "line_type": "text",
                    "line_order_in_block": 0,
                    "global_line_order": 0,
                    "bbox": [10, 10, 50, 20],
                    "gt_text": "worker-perf",
                    "gt_script": "latin",
                }
            ],
            "blocks": [{"block_id": 0, "block_type": "paragraph", "bbox": [10, 10, 50, 20]}],
            "gt_stats": {},
        }
        mt = np.zeros((64, 128), dtype=np.uint8)
        mt[10:30, 10:60] = 255
        mm = np.zeros((64, 128), dtype=np.uint8)
        img = np.full((64, 128, 3), 255, dtype=np.uint8)
        return {"image_u8": img, "mask_text_u8": mt, "mask_math_u8": mm, "ann": ann}

    def fake_validate_page(ann, mt, mm, _cfg):
        return True, None, {}

    monkeypatch.setattr(cli_mod, "load_config", fake_load_config)
    monkeypatch.setattr(cli_mod, "sample_page_spec", fake_sample_page_spec)
    monkeypatch.setattr(cli_mod, "render_page_layers", fake_render_page_layers)
    monkeypatch.setattr(cli_mod, "validate_page", fake_validate_page)

    out_root = tmp_path / "out"
    dirs = {
        "images": str(out_root / "images"),
        "masks": str(out_root / "masks"),
        "ann": str(out_root / "ann"),
        "gt": str(out_root / "gt"),
        "tmp": str(out_root / "_tmp"),
    }

    t0 = time.perf_counter()
    for i in range(5):
        res = cli_mod._worker_generate_validate_save(
            (
                i,
                f"{i:06d}",
                123,
                "configs/minimal_valid.yaml",
                dirs,
                {
                    "max_tries": 2,
                    "disable_augment_on_try": 2,
                    "jitter_seed_step": 1000,
                    "fallback_dpi": 300,
                },
            )
        )
        assert res["ok"] is True
    elapsed = time.perf_counter() - t0

    assert elapsed < 8.0



