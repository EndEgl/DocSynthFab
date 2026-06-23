# src/docsynthfab/cli/progress.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import time
from typing import Any

from docsynthfab.telemetry.progress import TelemetryError, TemperatureReader


def build_progress_line(
    *,
    total: int,
    ok: int,
    fail: int,
    start_time: float,
    qc_summary: dict[str, Any],
    temp_reader: TemperatureReader,
    telemetry_cfg: dict[str, Any],
) -> str:
    done_pages = ok + fail
    pct = 100.0 * done_pages / float(total)
    elapsed = max(1e-6, time.time() - start_time)
    rate = done_pages / elapsed
    eta_s = int((total - done_pages) / max(1e-6, rate))

    hh = eta_s // 3600
    mm_ = (eta_s % 3600) // 60
    ss = eta_s % 60

    tg = "NA"
    tc = "NA"

    try:
        tr = temp_reader.read()
        tg = f"{tr.gpu_c}C" if tr.gpu_c is not None else "NA"
        tc = f"{tr.cpu_c}C" if tr.cpu_c is not None else "NA"
    except TelemetryError:
        if bool(telemetry_cfg.get("temperature", {}).get("require_temp_sensor", True)):
            raise

    tstamp = time.strftime("%H:%M:%S")

    parts = [
        f"[{tstamp}] pages {done_pages:04d}/{total} ({pct:5.2f}%)",
        f"ok {ok}",
        f"fail {fail}",
        f"math {qc_summary['math_pages']}",
        f"mathmask {qc_summary['math_mask_nonempty_pages']}",
    ]

    if bool(telemetry_cfg.get("show_rate", True)):
        parts.append(f"rate {rate:.2f}/s")

    if bool(telemetry_cfg.get("show_eta", True)):
        parts.append(f"eta {hh:02d}:{mm_:02d}:{ss:02d}")

    parts.append(f"temp gpu={tg} cpu={tc}")

    return " | ".join(parts)



