# src/docsynthfab/qc/__init__.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

from .validators import validate_page, compute_density_metrics

__all__ = ["validate_page", "compute_density_metrics"]



