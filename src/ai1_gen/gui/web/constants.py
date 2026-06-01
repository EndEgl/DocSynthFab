# src/ai1_gen/gui/web/constants.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations


TERMINAL_RUN_STATES = {"done", "failed", "cancelled"}

# Excel often uses semicolon-separated CSV in Turkish/European regional settings.
# Export uses semicolon; import supports semicolon, comma, and tab.
CSV_EXPORT_DELIMITER = ";"