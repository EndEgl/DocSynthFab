# src/ai1_gen/latex/normalize.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# Purpose:
# - Normalize LaTeX expressions before sending them to the HTTP renderer.
# - Avoid regex replacement escape bugs such as:
#     re.error: bad escape \s at position 0
#
# Important:
# - Never pass a LaTeX command like r"\sum" directly as the replacement
#   string to re.sub(...). Use a callable replacement instead.

from __future__ import annotations

import re

from .errors import LatexRenderError


LATEX_COMMAND_FIXES = {
    "frac": r"\frac",
    "sqrt": r"\sqrt",
    "sum": r"\sum",
    "prod": r"\prod",
    "int": r"\int",
    "sin": r"\sin",
    "cos": r"\cos",
    "tan": r"\tan",
    "log": r"\log",
    "ln": r"\ln",
    "exp": r"\exp",
    "det": r"\det",
    "lim": r"\lim",
    "partial": r"\partial",
    "infty": r"\infty",
    "alpha": r"\alpha",
    "beta": r"\beta",
    "gamma": r"\gamma",
    "delta": r"\delta",
    "theta": r"\theta",
    "lambda": r"\lambda",
    "mu": r"\mu",
    "sigma": r"\sigma",
    "phi": r"\phi",
    "omega": r"\omega",
    "mid": r"\mid",
    "cap": r"\cap",
    "cup": r"\cup",
}


def _collapse_double_escaped_known_commands(text: str) -> str:
    """
    Convert known double-escaped LaTeX commands back to normal LaTeX commands.

    Example:
        "\\\\frac{a}{b}" -> "\\frac{a}{b}"

    This is plain string replacement, not regex replacement.
    """
    for command in LATEX_COMMAND_FIXES.values():
        double_escaped = command.replace("\\", "\\\\")
        text = text.replace(double_escaped, command)

    return text


def normalize_latex_expr(expr: str) -> str:
    """
    Normalize a LaTeX expression while keeping backward compatibility.

    Examples:
      sum_{i=1}^{n} i -> \\sum_{i=1}^{n} i
      sqrt{x+1}       -> \\sqrt{x+1}
      frac{a}{b}      -> \\frac{a}{b}
    """
    text = str(expr or "").strip()

    if not text:
        return ""

    # Already valid command.
    if text.startswith("\\"):
        return text

    # Backward compatibility for old generator/import paths.
    command_prefixes = (
        "sum_",
        "sum{",
        "int_",
        "int{",
        "sqrt",
        "frac",
        "alpha",
        "beta",
        "gamma",
        "theta",
        "lambda",
        "mu",
        "sigma",
    )

    for prefix in command_prefixes:
        if text.startswith(prefix):
            return "\\" + text

    return text