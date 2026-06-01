# src/ai1_gen/latex/errors.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations


class LatexRenderError(RuntimeError):
    """Raised when LaTeX rendering fails."""


class LatexDockerRuntimeError(RuntimeError):
    """Raised when the Docker-based LaTeX runtime cannot be prepared."""