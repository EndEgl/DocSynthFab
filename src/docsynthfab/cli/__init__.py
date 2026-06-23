# src/docsynthfab/cli/__init__.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - PyYAML>=6.0,<7.0

from __future__ import annotations

import concurrent.futures as cf

from docsynthfab.config import load_config
from docsynthfab.io.exporter import ensure_dataset_dirs

from .fallback import make_fallback_render as _make_fallback_render
from .fallback import make_fallback_render
from .gt_export import build_gt_export as _build_gt_export
from .gt_export import build_gt_export
from .main import main
from .splits import normalized_split_ratios as _normalized_split_ratios
from .splits import normalized_split_ratios
from .splits import split_of as _split_of
from .splits import split_of
from .worker import worker_generate_validate_save as _worker_generate_validate_save
from .worker import worker_generate_validate_save

__all__ = [
    "cf",
    "load_config",
    "ensure_dataset_dirs",
    "main",
    "build_gt_export",
    "_build_gt_export",
    "make_fallback_render",
    "_make_fallback_render",
    "normalized_split_ratios",
    "_normalized_split_ratios",
    "split_of",
    "_split_of",
    "worker_generate_validate_save",
    "_worker_generate_validate_save",
]



