# src/ai1_gen/config.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - PyYAML>=6.0,<7.0

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml


class ConfigError(ValueError):
    pass


def _norm_dist(d: Dict[str, float], err_code: str) -> Dict[str, float]:
    if not isinstance(d, dict) or not d:
        raise ConfigError(err_code)
    s = 0.0
    for k, v in d.items():
        try:
            fv = float(v)
        except Exception:
            raise ConfigError(err_code)
        if fv < 0:
            raise ConfigError(err_code)
        s += fv
    if s <= 0:
        raise ConfigError(err_code)
    return {k: float(v) / s for k, v in d.items()}


def _get(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


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
        return _norm_dist(_get(self.raw, "dist.density_dist", {}), "cfg/invalid-density-dist")

    def scale_dist(self) -> Dict[str, float]:
        return _norm_dist(_get(self.raw, "dist.scale_dist", {}), "cfg/invalid-scale-dist")

    def noise_dist(self) -> Dict[str, float]:
        return _norm_dist(_get(self.raw, "dist.noise_level_dist", {"clean": 0.3, "medium": 0.5, "heavy": 0.2}), "cfg/invalid-noise-dist")

    def dpi_choices(self) -> Tuple[int, ...]:
        xs = _get(self.raw, "page.dpi_choices", [200, 300])
        return tuple(int(x) for x in xs)

    def density_targets(self) -> Dict[str, Dict[str, Tuple[int, int]]]:
        # {level: {line_count_range:(a,b), block_count_range:(a,b)}}
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


def load_config(path: str | Path) -> AppConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError("cfg/invalid-yaml")
    return AppConfig(raw)


