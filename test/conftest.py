from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


class DummyCfg:
    def __init__(
        self,
        *,
        raw: dict | None = None,
        qc_cfg: dict | None = None,
        thresholds_cfg: dict | None = None,
        augment_cfg: dict | None = None,
        telemetry_cfg: dict | None = None,
        out_root: str = "out",
        pages: int = 4,
        workers: int = 1,
        seed: int = 123,
        version: str = "ai1-ds-v1.3.2",
    ) -> None:
        self.raw = raw or {}
        self._qc_cfg = qc_cfg or {}
        self._thresholds_cfg = thresholds_cfg or {}
        self._augment_cfg = augment_cfg or {"enable": False}
        self._telemetry_cfg = telemetry_cfg or {}
        self.out_root = out_root
        self.pages = pages
        self.workers = workers
        self.seed = seed
        self.version = version

    def qc(self):
        return self._qc_cfg

    def thresholds(self):
        return self._thresholds_cfg

    def augment(self):
        return self._augment_cfg

    def telemetry(self):
        return self._telemetry_cfg


@pytest.fixture
def dummy_cfg() -> DummyCfg:
    return DummyCfg(
        raw={
            "run": {
                "splits": {"train": 0.8, "val": 0.1, "test": 0.1},
            },
            "page": {
                "bg_color_rgb": [255, 255, 255],
            },
        },
        qc_cfg={
            "mask_binary_required": True,
            "overlap_text_over_math_max_ratio": 0.01,
            "require_global_line_order_contiguous": True,
            "require_title_near_top": False,
            "require_caption_near_target": False,
            "use_page_family_rules": False,
            "soft_reading_order_check": False,
            "max_block_overlap_ratio_min_area": 0.35,
        },
        thresholds_cfg={},
        augment_cfg={"enable": False},
        telemetry_cfg={
            "mode": "single_line",
            "ascii_only": True,
            "show_eta": True,
            "show_rate": True,
            "update_interval_s": 1.2,
            "temperature": {
                "require_temp_sensor": False,
                "prefer_gpu": True,
            },
        },
    )


@pytest.fixture
def ann_minimal_dict() -> dict:
    return {
        "version": "ai1-ds-v1.3.2",
        "page_id": "000001",
        "size": {"w": 200, "h": 100, "dpi": 300},
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
        "gt_page_text": "Hello world",
        "lines": [
            {
                "line_id": 0,
                "block_id": 0,
                "line_type": "text",
                "line_order_in_block": 0,
                "global_line_order": 0,
                "bbox": [10, 10, 80, 20],
                "gt_text": "Hello world",
                "gt_script": "latin",
            }
        ],
        "blocks": [
            {
                "block_id": 0,
                "block_type": "paragraph",
                "bbox": [10, 10, 80, 20],
            }
        ],
        "gt_stats": {},
    }


@pytest.fixture
def ann_math_dict() -> dict:
    return {
        "version": "ai1-ds-v1.3.2",
        "page_id": "000002",
        "size": {"w": 200, "h": 100, "dpi": 300},
        "meta": {
            "density_level": "normal",
            "scale_profile": "dpi300",
            "noise_level": "clean",
            "page_family": "report",
            "has_table": False,
            "has_equation": True,
            "has_equation_layout": True,
            "has_figure": False,
        },
        "gt_page_text": "x^2 + y^2 = z^2",
        "lines": [
            {
                "line_id": 0,
                "block_id": 0,
                "line_type": "math",
                "line_order_in_block": 0,
                "global_line_order": 0,
                "bbox": [20, 20, 100, 20],
                "gt_latex": r"x^2 + y^2 = z^2",
            }
        ],
        "blocks": [
            {
                "block_id": 0,
                "block_type": "equation",
                "bbox": [20, 20, 100, 20],
            }
        ],
        "gt_stats": {},
    }


@pytest.fixture
def mask_text_u8() -> np.ndarray:
    m = np.zeros((100, 200), dtype=np.uint8)
    m[10:30, 10:90] = 255
    return m


@pytest.fixture
def mask_math_u8() -> np.ndarray:
    m = np.zeros((100, 200), dtype=np.uint8)
    m[20:40, 20:120] = 255
    return m


@pytest.fixture
def rgb_image_u8() -> np.ndarray:
    return np.full((100, 200, 3), 255, dtype=np.uint8)


@pytest.fixture
def write_json_fixture(tmp_path: Path):
    def _write(rel_path: str, data: dict | list | str) -> Path:
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, (dict, list)):
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            path.write_text(str(data), encoding="utf-8")
        return path
    return _write