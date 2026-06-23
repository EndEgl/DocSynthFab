# src/docsynthfab/config/__init__.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - PyYAML>=6.0,<7.0

from __future__ import annotations

from .config import AppConfig
from .errors import ConfigError
from .helpers import _get, _norm_dist, get_nested, normalize_distribution
from .loader import load_config

__all__ = [
    "AppConfig",
    "ConfigError",
    "load_config",
    "_get",
    "_norm_dist",
    "get_nested",
    "normalize_distribution",
]



