from __future__ import annotations

import random
import time

import numpy as np

from docsynthfab.augment.apply_augment import apply_augment


def test_augment_perf_smoke():
    img = np.full((512, 512, 3), 255, dtype=np.uint8)
    mt = np.zeros((512, 512), dtype=np.uint8)
    mm = np.zeros((512, 512), dtype=np.uint8)
    mt[50:200, 50:300] = 255

    ann = {
        "version": "docsynthfab-ds-v0.1",
        "page_id": "000001",
        "size": {"w": 512, "h": 512, "dpi": 300},
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
        "gt_page_text": "perf",
        "lines": [
            {
                "line_id": 0,
                "block_id": 0,
                "line_type": "text",
                "line_order_in_block": 0,
                "global_line_order": 0,
                "bbox": [50, 50, 250, 150],
                "gt_text": "perf",
                "gt_script": "latin",
            }
        ],
        "blocks": [{"block_id": 0, "block_type": "paragraph", "bbox": [50, 50, 250, 150]}],
        "gt_stats": {},
    }

    aug_cfg = {
        "selection_policy": {
            "clean": {
                "p_photometric": 1.0,
                "p_blur_noise": 1.0,
                "p_capture": 0.0,
                "p_geometry": 0.0,
                "p_edge": 0.0,
                "p_elastic": 0.0,
            }
        },
        "photometric": {"gamma": [1.0, 1.0], "brightness": [0, 0], "contrast": [1.0, 1.0]},
        "blur_noise": {"gaussian_kernel_choices": [3]},
        "capture_sim": {},
        "geometry": {},
        "edge_degredation": {},
        "elastic_distortion": {},
    }

    t0 = time.perf_counter()
    for i in range(5):
        rng = random.Random(100 + i)
        out = apply_augment(img, mt, mm, ann, ann["meta"], aug_cfg, rng)
        assert out.image_aug_u8.shape == img.shape
    elapsed = time.perf_counter() - t0

    assert elapsed < 5.0



