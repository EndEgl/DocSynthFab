# src/ai1_gen/layout/__init__.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from .layout_sampler import sample_page_spec
from .specs import BlockSpec, LineSpec, PageSpec

__all__ = ["sample_page_spec", "PageSpec", "BlockSpec", "LineSpec"]