# src/docsynthfab/reports/io_utils.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# This module uses only the Python standard library.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _now_utc_iso() -> str:
    """Return a stable UTC ISO timestamp without microseconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    """Read a UTF-8 JSON object from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    """Write a UTF-8 JSON file with readable indentation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    """Write a UTF-8 text file and ensure it ends with one newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _safe_float(x: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    """Safely convert a value to int."""
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _bool_int(x: Any) -> int:
    """Convert truthiness to 0/1 for CSV-friendly feature rows."""
    return 1 if bool(x) else 0


def _bbox_area_xywh(bbox: Any) -> float:
    """Return the area of an XYWH bbox-like list."""
    if not isinstance(bbox, list) or len(bbox) < 4:
        return 0.0

    return max(0.0, _safe_float(bbox[2])) * max(0.0, _safe_float(bbox[3]))



