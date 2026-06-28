# src/docsynthfab/config/helpers.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import Any, Dict


def _norm_dist(d: Dict[str, float], err_code: str) -> Dict[str, float]:
    from .errors import ConfigError

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


get_nested = _get

def normalize_distribution(
    d,
    *,
    keys=None,
    err_code="cfg/invalid-distribution",
):
    out = _norm_dist(d, err_code)

    if keys is not None:
        return {k: out.get(k, 0.0) for k in keys}

    return out



