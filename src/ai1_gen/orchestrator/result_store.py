# src/ai1_gen/orchestrator/result_store.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .models import RunSummary


def _read_json_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def tail_text(path: str | Path, max_chars: int = 4000) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    txt = p.read_text(encoding="utf-8", errors="replace")
    if len(txt) <= max_chars:
        return txt
    return txt[-max_chars:]


def build_run_summary(run_id: str, out_root: str, state: str) -> RunSummary:
    out_dir = Path(out_root)
    qc_summary_path = out_dir / "qc_summary.json"
    run_log_path = out_dir / "run.log"
    gt_jsonl_path = out_dir / "gt_pages.jsonl"
    train_split_path = out_dir / "splits" / "train.txt"
    val_split_path = out_dir / "splits" / "val.txt"
    test_split_path = out_dir / "splits" / "test.txt"

    qc = _read_json_if_exists(qc_summary_path) or {}

    return RunSummary(
        run_id=run_id,
        state=state,
        out_root=str(out_dir),
        qc_summary_path=str(qc_summary_path) if qc_summary_path.exists() else None,
        run_log_path=str(run_log_path) if run_log_path.exists() else None,
        gt_jsonl_path=str(gt_jsonl_path) if gt_jsonl_path.exists() else None,
        train_split_path=str(train_split_path) if train_split_path.exists() else None,
        val_split_path=str(val_split_path) if val_split_path.exists() else None,
        test_split_path=str(test_split_path) if test_split_path.exists() else None,
        total=qc.get("total"),
        ok=qc.get("ok"),
        fail=qc.get("fail"),
        recovered=qc.get("recovered"),
        fallback_used=qc.get("fallback_used"),
        math_pages=qc.get("math_pages"),
        math_mask_nonempty_pages=qc.get("math_mask_nonempty_pages"),
        extra=qc,
    )