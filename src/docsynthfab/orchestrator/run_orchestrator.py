# src/docsynthfab/orchestrator/run_orchestrator.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - PyYAML>=6.0,<7.0

from __future__ import annotations

import copy
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, List

import yaml

from .job_runner import JobRunner
from .models import RunProgress, RunRequest, RunStatus
from .param_schema import get_param_schema
from .result_store import build_run_summary, tail_text


def _deep_get(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _deep_set(d: Dict[str, Any], path: str, value: Any) -> None:
    cur = d
    parts = path.split(".")
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _deep_merge_dicts(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge_dicts(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _default_user_config_path(config_path: str | Path) -> Path:
    p = Path(config_path)
    return p.with_name(f"{p.stem}.user.yaml")


def _read_yaml_dict(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"orch/invalid-yaml-dict: {p}")
    return raw


def _write_yaml_dict(path: str | Path, data: Dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump(data or {}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return p


class RunOrchestrator:
    def __init__(self, work_root: str | Path = ".ai1_orchestrator") -> None:
        self.work_root = Path(work_root)
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.job_runner = JobRunner()
        self._runs: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate_request(self, request: RunRequest) -> None:
        if not request.config_path:
            raise ValueError("orch/missing-config-path")
        if not Path(request.config_path).exists():
            raise FileNotFoundError(request.config_path)
        if request.pages < 0:
            raise ValueError("orch/invalid-pages")
        if request.workers < 0:
            raise ValueError("orch/invalid-workers")
        if request.seed < -1:
            raise ValueError("orch/invalid-seed")

    # ------------------------------------------------------------------
    # Baseline / user config paths
    # ------------------------------------------------------------------
    def get_user_config_path(self, config_path: str | Path) -> Path:
        return _default_user_config_path(config_path)

    def load_user_override_dict(self, config_path: str | Path) -> Dict[str, Any]:
        return _read_yaml_dict(self.get_user_config_path(config_path))

    def save_user_override_dict(
        self,
        config_path: str | Path,
        override_dict: Dict[str, Any],
    ) -> Path:
        return _write_yaml_dict(self.get_user_config_path(config_path), override_dict)

    def reset_user_override_dict(self, config_path: str | Path) -> Path:
        return _write_yaml_dict(self.get_user_config_path(config_path), {})

    # ------------------------------------------------------------------
    # Config loaders
    # ------------------------------------------------------------------
    def load_config_dict(self, config_path: str | Path) -> Dict[str, Any]:
        raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError("orch/invalid-config-yaml")
        return raw

    def get_baseline_config_dict(self, config_path: str | Path) -> Dict[str, Any]:
        return copy.deepcopy(self.load_config_dict(config_path))

    def get_baseline_yaml_text(self, config_path: str | Path) -> str:
        raw = self.get_baseline_config_dict(config_path)
        return yaml.safe_dump(raw, sort_keys=False, allow_unicode=True)

    # ------------------------------------------------------------------
    # YAML override helpers
    # ------------------------------------------------------------------
    def parse_raw_yaml_override(self, yaml_text: str | None) -> Dict[str, Any]:
        if not yaml_text or not str(yaml_text).strip():
            return {}
        parsed = yaml.safe_load(yaml_text)
        if parsed is None:
            return {}
        if not isinstance(parsed, dict):
            raise ValueError("orch/invalid-raw-yaml-override")
        return parsed

    def merge_raw_yaml_override(
        self,
        base_cfg: Dict[str, Any],
        raw_yaml_text: str | None,
    ) -> Dict[str, Any]:
        override_dict = self.parse_raw_yaml_override(raw_yaml_text)
        if not override_dict:
            return copy.deepcopy(base_cfg)
        return _deep_merge_dicts(base_cfg, override_dict)

    # ------------------------------------------------------------------
    # Baseline + user override merge
    # ------------------------------------------------------------------
    def build_config_with_user_override(
        self,
        config_path: str | Path,
        overrides: Optional[Dict[str, Any]] = None,
        raw_yaml_override_text: str | None = None,
    ) -> Dict[str, Any]:
        base_cfg = self.get_baseline_config_dict(config_path)
        user_cfg = self.load_user_override_dict(config_path)

        cfg = _deep_merge_dicts(base_cfg, user_cfg)

        for key, value in (overrides or {}).items():
            _deep_set(cfg, key, value)

        cfg = self.merge_raw_yaml_override(cfg, raw_yaml_override_text)
        return cfg

    # ------------------------------------------------------------------
    # GUI helpers
    # ------------------------------------------------------------------
    def build_config_from_overrides(
        self,
        config_path: str | Path,
        overrides: Optional[Dict[str, Any]] = None,
        raw_yaml_override_text: str | None = None,
    ) -> Dict[str, Any]:
        return self.build_config_with_user_override(
            config_path=config_path,
            overrides=overrides,
            raw_yaml_override_text=raw_yaml_override_text,
        )

    def build_effective_config_preview(
        self,
        config_path: str | Path,
        overrides: Optional[Dict[str, Any]] = None,
        raw_yaml_override_text: str | None = None,
        out_root: str | None = None,
        pages: int = 0,
        workers: int = 0,
        seed: int = -1,
        smoke_test: bool = False,
        export_targets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        cfg = self.build_config_with_user_override(
            config_path=config_path,
            overrides=overrides,
            raw_yaml_override_text=raw_yaml_override_text,
        )

        if out_root:
            _deep_set(cfg, "io.out_root", out_root)
        if pages > 0:
            _deep_set(cfg, "run.pages", pages)
        if workers > 0:
            _deep_set(cfg, "run.workers", workers)
        if seed >= 0:
            _deep_set(cfg, "run.seed", seed)

        if export_targets:
            clean_targets = [
                str(x).strip().lower()
                for x in export_targets
                if str(x).strip()
            ]
            if clean_targets:
                _deep_set(cfg, "run.export_targets", clean_targets)

        if smoke_test:
            _deep_set(cfg, "run.pages", min(int(_deep_get(cfg, "run.pages", 10)), 10))
            _deep_set(cfg, "run.workers", max(1, min(int(_deep_get(cfg, "run.workers", 1)), 2)))


        return cfg

    def build_effective_config_yaml_text(
        self,
        config_path: str | Path,
        overrides: Optional[Dict[str, Any]] = None,
        raw_yaml_override_text: str | None = None,
        out_root: str | None = None,
        pages: int = 0,
        workers: int = 0,
        seed: int = -1,
        smoke_test: bool = False,
        export_targets: Optional[List[str]] = None,
    ) -> str:
        cfg = self.build_effective_config_preview(
            config_path=config_path,
            overrides=overrides,
            raw_yaml_override_text=raw_yaml_override_text,
            out_root=out_root,
            pages=pages,
            workers=workers,
            seed=seed,
            smoke_test=smoke_test,
            export_targets=export_targets,
        )
        return yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)

    def reset_overrides_to_baseline(self, config_path: str | Path) -> Dict[str, Any]:
        self.reset_user_override_dict(config_path)
        return {}

    def get_default_value_map(self, visibility: str | None = None) -> Dict[str, Any]:
        schema = get_param_schema()
        if visibility is not None:
            schema = [f for f in schema if f.visibility == visibility]
        return {field.key: copy.deepcopy(field.default) for field in schema}

    def build_baseline_override_map(
        self,
        config_path: str | Path,
        visibility: str | None = None,
    ) -> Dict[str, Any]:
        cfg = self.get_baseline_config_dict(config_path)
        schema = get_param_schema()
        if visibility is not None:
            schema = [f for f in schema if f.visibility == visibility]

        out: Dict[str, Any] = {}
        for field in schema:
            out[field.key] = copy.deepcopy(_deep_get(cfg, field.key, field.default))
        return out

    # ------------------------------------------------------------------
    # Main run config builder
    # ------------------------------------------------------------------
    def build_effective_config_dict(self, request: RunRequest) -> Dict[str, Any]:
        raw = self.build_config_with_user_override(
            config_path=request.config_path,
            overrides=request.overrides,
            raw_yaml_override_text=getattr(request, "raw_yaml_override_text", None),
        )

        if request.out_root:
            _deep_set(raw, "io.out_root", request.out_root)
        if request.pages > 0:
            _deep_set(raw, "run.pages", request.pages)
        if request.workers > 0:
            _deep_set(raw, "run.workers", request.workers)
        if request.seed >= 0:
            _deep_set(raw, "run.seed", request.seed)

        if getattr(request, "export_targets", None):
            clean_targets = [
                str(x).strip().lower()
                for x in request.export_targets
                if str(x).strip()
            ]
            if clean_targets:
                _deep_set(raw, "run.export_targets", clean_targets)

        if request.smoke_test:
            _deep_set(raw, "run.pages", min(int(_deep_get(raw, "run.pages", 10)), 10))
            _deep_set(raw, "run.workers", max(1, min(int(_deep_get(raw, "run.workers", 1)), 2)))

            
        return raw

    def save_effective_config(self, run_id: str, cfg_obj: Dict[str, Any]) -> Path:
        run_dir = self.work_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / "effective_config.yaml"
        path.write_text(
            yaml.safe_dump(cfg_obj, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return path

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------
    def start(self, request: RunRequest) -> str:
        self.validate_request(request)

        run_id = uuid.uuid4().hex[:12]
        run_dir = self.work_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        effective_cfg = self.build_effective_config_dict(request)
        effective_cfg_path = self.save_effective_config(run_id, effective_cfg)

        out_root = str(_deep_get(effective_cfg, "io.out_root", request.out_root or ""))

        stdout_log = run_dir / "stdout.log"
        stderr_log = run_dir / "stderr.log"

        proc = self.job_runner.start_subprocess_run(
            request,
            effective_config_path=str(effective_cfg_path),
            stdout_log_path=str(stdout_log),
            stderr_log_path=str(stderr_log),
        )

        self._runs[run_id] = {
            "request": request,
            "process": proc,
            "started_at": time.time(),
            "finished_at": None,
            "config_path": request.config_path,
            "effective_config_path": str(effective_cfg_path),
            "out_root": out_root,
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "cancelled": False,
        }
        return run_id

    def _compute_state(self, run_id: str) -> str:
        rec = self._runs[run_id]
        proc = rec["process"]

        if rec.get("cancelled", False):
            return "cancelled"

        rc = proc.poll()
        if rc is None:
            return "running"
        if rc == 0:
            return "done"
        return "failed"

    def get_status(self, run_id: str) -> RunStatus:
        if run_id not in self._runs:
            raise KeyError("orch/unknown-run-id")

        rec = self._runs[run_id]
        proc = rec["process"]
        state = self._compute_state(run_id)

        if state in {"done", "failed", "cancelled"} and rec.get("finished_at") is None:
            rec["finished_at"] = time.time()

        progress = RunProgress(
            run_id=run_id,
            state=state,
            message="",
        )

        return RunStatus(
            run_id=run_id,
            state=state,
            pid=proc.pid,
            started_at=rec.get("started_at"),
            finished_at=rec.get("finished_at"),
            config_path=rec.get("config_path"),
            effective_config_path=rec.get("effective_config_path"),
            out_root=rec.get("out_root"),
            stdout_log=rec.get("stdout_log"),
            stderr_log=rec.get("stderr_log"),
            return_code=proc.poll(),
            error=None if state != "failed" else tail_text(rec.get("stderr_log", ""), 2000),
            progress=progress,
        )

    def get_summary(self, run_id: str):
        if run_id not in self._runs:
            raise KeyError("orch/unknown-run-id")
        rec = self._runs[run_id]
        state = self._compute_state(run_id)
        return build_run_summary(run_id, rec["out_root"], state)

    def cancel(self, run_id: str) -> bool:
        if run_id not in self._runs:
            return False
        rec = self._runs[run_id]
        proc = rec["process"]
        if proc.poll() is not None:
            return False
        proc.terminate()
        rec["cancelled"] = True
        rec["finished_at"] = time.time()
        return True

    def list_runs(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for run_id in self._runs:
            out[run_id] = self.get_status(run_id).to_dict()
        return out

    # ------------------------------------------------------------------
    # UI schema
    # ------------------------------------------------------------------
    def get_schema_for_ui(self, visibility: str | None = None):
        schema = get_param_schema()
        if visibility is not None:
            schema = [f for f in schema if f.visibility == visibility]
        return [f.to_dict() for f in schema]



