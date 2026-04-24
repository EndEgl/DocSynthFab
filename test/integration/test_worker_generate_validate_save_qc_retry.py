from __future__ import annotations

import numpy as np

import ai1_gen.cli as cli_mod


class CfgStub:
    def __init__(self) -> None:
        self.raw = {"page": {"bg_color_rgb": [255, 255, 255]}}

    def augment(self):
        return {"enable": False}

    version = "ai1-ds-v1.3.2"


def test_worker_generate_validate_save_recovers_after_qc_retry(tmp_path, monkeypatch):
    cfg = CfgStub()
    validate_calls = {"n": 0}

    def fake_load_config(_path):
        return cfg

    def fake_sample_page_spec(_cfg, _rng, _idx, page_id):
        return {"page_id": page_id}

    def fake_render_page_layers(_ps, _cfg, _rng):
        ann = {
            "version": "ai1-ds-v1.3.2",
            "page_id": "000002",
            "size": {"w": 64, "h": 32, "dpi": 300},
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
            "gt_page_text": "retry-ok",
            "lines": [
                {
                    "line_id": 0,
                    "block_id": 0,
                    "line_type": "text",
                    "line_order_in_block": 0,
                    "global_line_order": 0,
                    "bbox": [5, 5, 20, 10],
                    "gt_text": "retry-ok",
                    "gt_script": "latin",
                }
            ],
            "blocks": [{"block_id": 0, "block_type": "paragraph", "bbox": [5, 5, 20, 10]}],
            "gt_stats": {},
        }
        mt = np.zeros((32, 64), dtype=np.uint8)
        mt[5:15, 5:25] = 255
        mm = np.zeros((32, 64), dtype=np.uint8)
        img = np.full((32, 64, 3), 255, dtype=np.uint8)
        return {"image_u8": img, "mask_text_u8": mt, "mask_math_u8": mm, "ann": ann}

    def fake_validate_page(_ann, _mt, _mm, _cfg):
        validate_calls["n"] += 1
        if validate_calls["n"] == 1:
            return False, "qc/order-not-contiguous", {"expected": 0, "found": 9}
        return True, None, {"ok": True}

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

    res = cli_mod._worker_generate_validate_save(
        (
            0,
            "000002",
            123,
            "relative/config.yaml",
            dirs,
            {
                "max_tries": 3,
                "disable_augment_on_try": 2,
                "jitter_seed_step": 1000,
                "fallback_dpi": 300,
            },
        )
    )

    assert res["ok"] is True
    assert validate_calls["n"] >= 2
    assert len(res["recovered_from"]) >= 1
    assert res["recovered_from"][0]["kind"] == "qc_fail"
    assert (out_root / "gt" / "000002.json").exists()