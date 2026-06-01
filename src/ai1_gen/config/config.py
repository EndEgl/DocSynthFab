# src/ai1_gen/config/config.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .helpers import _get, _norm_dist


@dataclass(frozen=True)
class AppConfig:
    raw: Dict[str, Any]

    @property
    def version(self) -> str:
        return str(_get(self.raw, "project.version", "ai1-ds-v1.3.2"))

    @property
    def out_root(self) -> str:
        return str(_get(self.raw, "io.out_root", r"D:\ai1_dataset_v1"))

    @property
    def tmp_dir_name(self) -> str:
        return str(_get(self.raw, "io.tmp_dir", "_tmp"))

    @property
    def pages(self) -> int:
        return int(_get(self.raw, "run.pages", 3000))

    @property
    def seed(self) -> int:
        return int(_get(self.raw, "run.seed", 1337))

    @property
    def workers(self) -> int:
        return int(_get(self.raw, "run.workers", 6))

    def density_dist(self) -> Dict[str, float]:
        return _norm_dist(
            _get(self.raw, "dist.density_dist", {}),
            "cfg/invalid-density-dist",
        )

    def scale_dist(self) -> Dict[str, float]:
        return _norm_dist(
            _get(self.raw, "dist.scale_dist", {}),
            "cfg/invalid-scale-dist",
        )

    def noise_dist(self) -> Dict[str, float]:
        return _norm_dist(
            _get(
                self.raw,
                "dist.noise_level_dist",
                {"clean": 0.3, "medium": 0.5, "heavy": 0.2},
            ),
            "cfg/invalid-noise-dist",
        )

    def dpi_choices(self) -> Tuple[int, ...]:
        xs = _get(self.raw, "page.dpi_choices", [200, 300])
        return tuple(int(x) for x in xs)

    def page_size_dist(self) -> Dict[str, float]:
        return _norm_dist(
            _get(
                self.raw,
                "page.size_dist",
                {
                    "a4_portrait": 0.60,
                    "letter_portrait": 0.20,
                    "a4_landscape": 0.10,
                    "letter_landscape": 0.10,
                },
            ),
            "cfg/invalid-page-size-dist",
        )

    def default_page_size(self) -> str:
        return str(_get(self.raw, "page.default_size", "a4_portrait"))

    def density_targets(self) -> Dict[str, Dict[str, Tuple[int, int]]]:
        t = _get(self.raw, "layout.targets", {})
        out: Dict[str, Dict[str, Tuple[int, int]]] = {}

        for lvl, spec in t.items():
            if not isinstance(spec, dict):
                continue

            lr = spec.get("line_count_range", [20, 60])
            br = spec.get("block_count_range", [5, 15])

            out[str(lvl)] = {
                "line_count_range": (int(lr[0]), int(lr[1])),
                "block_count_range": (int(br[0]), int(br[1])),
            }

        return out

    def thresholds(self) -> Dict[str, Any]:
        out = _get(self.raw, "density_thresholds", None)

        if isinstance(out, dict) and out:
            return out

        return _get(self.raw, "thresholds", {})

    def telemetry(self) -> Dict[str, Any]:
        return _get(self.raw, "telemetry", {})

    def augment(self) -> Dict[str, Any]:
        return _get(self.raw, "augment", {})

    def render(self) -> Dict[str, Any]:
        return _get(self.raw, "render", {})

    def qc(self) -> Dict[str, Any]:
        return _get(self.raw, "qc", {})

    def dist_tolerance_abs(self) -> float:
        return float(_get(self.raw, "qc.dist_tolerance_abs", 0.03))