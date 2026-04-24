# src/ai1_gen/orchestrator/models.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ParamField:
    key: str
    label: str
    group: str
    field_type: str  # int | float | bool | str | enum | path | color_rgb | json
    default: Any = None
    help_text: str = ""
    choices: List[Any] = field(default_factory=list)
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    step: Optional[float] = None
    required: bool = False
    visibility: str = "basic"   # basic | advanced
    advanced: bool = False      # geriye dönük uyumluluk için tutulabilir

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        if self.visibility == "advanced":
            out["advanced"] = True
        return out

@dataclass
class RunRequest:
    config_path: str
    out_root: str
    pages: int = 0
    workers: int = 0
    seed: int = -1
    preset_name: Optional[str] = None
    smoke_test: bool = False
    overrides: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RunProgress:
    run_id: str
    state: str  # queued | running | done | failed | cancelled
    pages_total: Optional[int] = None
    pages_ok: Optional[int] = None
    pages_fail: Optional[int] = None
    eta_seconds: Optional[int] = None
    rate_per_second: Optional[float] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RunStatus:
    run_id: str
    state: str
    pid: Optional[int] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    config_path: Optional[str] = None
    effective_config_path: Optional[str] = None
    out_root: Optional[str] = None
    stdout_log: Optional[str] = None
    stderr_log: Optional[str] = None
    return_code: Optional[int] = None
    error: Optional[str] = None
    progress: Optional[RunProgress] = None

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        if self.progress is not None:
            out["progress"] = self.progress.to_dict()
        return out


@dataclass
class RunSummary:
    run_id: str
    state: str
    out_root: str
    qc_summary_path: Optional[str] = None
    run_log_path: Optional[str] = None
    gt_jsonl_path: Optional[str] = None
    train_split_path: Optional[str] = None
    val_split_path: Optional[str] = None
    test_split_path: Optional[str] = None
    total: Optional[int] = None
    ok: Optional[int] = None
    fail: Optional[int] = None
    recovered: Optional[int] = None
    fallback_used: Optional[int] = None
    math_pages: Optional[int] = None
    math_mask_nonempty_pages: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)