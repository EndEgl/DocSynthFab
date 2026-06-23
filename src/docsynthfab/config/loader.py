# src/docsynthfab/config/loader.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - PyYAML>=6.0,<7.0

from __future__ import annotations

from pathlib import Path

import yaml

from .config import AppConfig
from .errors import ConfigError
from .helpers import _norm_dist


def load_config(path: str | Path) -> AppConfig:
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(str(p))

    raw = yaml.safe_load(p.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ConfigError("cfg/invalid-yaml")

    run = raw.get("run")

    if not isinstance(run, dict) or not run:
        raise ConfigError("cfg/missing-run-section")

    _norm_dist(run.get("splits", {}), "cfg/invalid-split-distribution")

    return AppConfig(raw)



