# src/ai1_gen/cli/run_loop.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ai1_gen.io.exporter import save_json
from ai1_gen.telemetry.progress import ProgressPrinter, TemperatureReader, TelemetryError

from .progress import build_progress_line
from .worker import worker_generate_validate_save


@dataclass
class RunLoopResult:
    ok: int
    fail: int
    produced_ids: list[str]
    qc_summary: Dict[str, Any]
    abort_reason: Optional[str]
    root_dir: Path
    run_log: Path


def make_initial_qc_summary(cfg: Any, total: int) -> Dict[str, Any]:
    return {
        "version": getattr(cfg, "version", "ai1-ds-v1.3.2"),
        "total": total,
        "ok": 0,
        "fail": 0,
        "errors": {},
        "density": {},
        "scale": {},
        "recovered": 0,
        "fallback_used": 0,
        "math_pages": 0,
        "math_layout_pages": 0,
        "math_mask_nonempty_pages": 0,
    }


def run_generation_loop(
    *,
    cfg: Any,
    cfg_path: str,
    dirs: Dict[str, Path],
    total: int,
    workers: int,
    seed: int,
    run_cfg: Dict[str, Any],
) -> RunLoopResult:
    import ai1_gen.cli as cli_pkg

    fail_fast = bool(run_cfg.get("fail_fast", False))
    max_fail_ratio = float(run_cfg.get("max_fail_ratio", 0.02))

    tel = cfg.telemetry()

    pp = ProgressPrinter(
        mode=str(tel.get("mode", "single_line")),
        ascii_only=bool(tel.get("ascii_only", True)),
    )
    temp_reader = TemperatureReader(
        require=bool(tel.get("temperature", {}).get("require_temp_sensor", True)),
        prefer_gpu=bool(tel.get("temperature", {}).get("prefer_gpu", True)),
        throttle_s=float(tel.get("update_interval_s", 1.2)),
    )

    page_ids = [f"{i:06d}" for i in range(total)]

    ok = 0
    fail = 0
    start = time.time()
    last_tick = 0.0
    abort_reason: Optional[str] = None

    qc_summary = make_initial_qc_summary(cfg, total)

    root_dir = Path(dirs.get("root", Path(".")))
    failed_log = root_dir / "failed_pages.log"
    errors_jsonl = root_dir / "errors.jsonl"
    run_log = root_dir / "run.log"
    gt_jsonl_path = root_dir / "gt_pages.jsonl"

    failed_log.parent.mkdir(parents=True, exist_ok=True)
    errors_jsonl.parent.mkdir(parents=True, exist_ok=True)
    run_log.parent.mkdir(parents=True, exist_ok=True)
    gt_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    Path(dirs["splits"]).mkdir(parents=True, exist_ok=True)

    jsonl_flush_batch_size = int(run_cfg.get("jsonl_flush_batch_size", 50))
    jsonl_buffer: list[str] = []

    dirs_str = {
        "images": str(dirs["images"]),
        "masks": str(dirs["masks"]),
        "ann": str(dirs["ann"]),
        "gt": str(dirs["gt"]),
        "tmp": str(dirs["tmp"]),
    }

    worker_cfg = run_cfg.get("worker", {}) or {}
    worker_options = {
        "max_tries": int(worker_cfg.get("max_tries", 4)),
        "disable_augment_on_try": int(worker_cfg.get("disable_augment_on_try", 2)),
        "jitter_seed_step": int(worker_cfg.get("jitter_seed_step", 10_000_019)),
        "fallback_dpi": int(worker_cfg.get("fallback_dpi", 300)),
    }

    max_pending_mult = float(run_cfg.get("max_pending_mult", 2.0))
    max_pending_min = int(run_cfg.get("max_pending_min", 8))
    max_pending = max(int(max_pending_mult * workers), max_pending_min)

    produced_ids: list[str] = []

    with (
        failed_log.open("a", encoding="utf-8") as failed_f,
        errors_jsonl.open("a", encoding="utf-8") as err_f,
        gt_jsonl_path.open("w", encoding="utf-8") as gt_f,
        cli_pkg.cf.ProcessPoolExecutor(max_workers=workers) as ex,
    ):
        pending: set[Any] = set()
        fut_to_pid: dict[Any, str] = {}

        it = iter(enumerate(page_ids))

        for _ in range(min(max_pending, total)):
            idx, pid = next(it)
            fut = ex.submit(
                worker_generate_validate_save,
                (idx, pid, seed, str(Path(cfg_path).resolve()), dirs_str, worker_options),
            )
            pending.add(fut)
            fut_to_pid[fut] = pid

        done_count = 0

        while pending and abort_reason is None:
            done, pending = cli_pkg.cf.wait(pending, return_when=cli_pkg.cf.FIRST_COMPLETED)

            for fut in done:
                done_count += 1
                pid_hint = fut_to_pid.pop(fut, "?")

                try:
                    res = fut.result()
                    if not res.get("ok", False):
                        fail += 1
                        _record_failed_result(
                            pid_hint=pid_hint,
                            result=res,
                            qc_summary=qc_summary,
                            failed_f=failed_f,
                            err_f=err_f,
                        )
                    else:
                        pid = str(res.get("page_id", pid_hint))
                        produced_ids.append(pid)
                        ok += 1

                        line = res.get("jsonl_line", "")
                        if line:
                            jsonl_buffer.append(line)
                            if len(jsonl_buffer) >= jsonl_flush_batch_size:
                                gt_f.writelines(jsonl_buffer)
                                gt_f.flush()
                                jsonl_buffer.clear()

                        _record_success_meta(pid=pid, result=res, qc_summary=qc_summary, err_f=err_f)

                except Exception as e:
                    fail += 1
                    _record_future_exception(
                        pid_hint=pid_hint,
                        exc=e,
                        qc_summary=qc_summary,
                        failed_f=failed_f,
                        err_f=err_f,
                    )

                processed = ok + fail
                if processed > 0:
                    live_fail_ratio = fail / processed
                    if fail_fast and fail > 0:
                        abort_reason = "run/fail-fast-triggered"
                    elif live_fail_ratio > max_fail_ratio:
                        abort_reason = f"run/max-fail-ratio-exceeded ({live_fail_ratio:.4f} > {max_fail_ratio:.4f})"

                now = time.time()
                if now - last_tick >= float(tel.get("update_interval_s", 1.2)) or done_count == total:
                    last_tick = now
                    try:
                        pp.print_line(
                            build_progress_line(
                                total=total,
                                ok=ok,
                                fail=fail,
                                start_time=start,
                                qc_summary=qc_summary,
                                temp_reader=temp_reader,
                                telemetry_cfg=tel,
                            )
                        )
                    except TelemetryError:
                        raise SystemExit("telemetry/no-temp-sensor")

                if abort_reason is not None:
                    for pf in pending:
                        pf.cancel()
                    break

                for _ in range(len(done)):
                    try:
                        idx, pid = next(it)
                    except StopIteration:
                        break

                    nf = ex.submit(
                        worker_generate_validate_save,
                        (idx, pid, seed, str(Path(cfg_path).resolve()), dirs_str, worker_options),
                    )
                    pending.add(nf)
                    fut_to_pid[nf] = pid

        if jsonl_buffer:
            gt_f.writelines(jsonl_buffer)
            gt_f.flush()
            jsonl_buffer.clear()

    pp.finish()

    qc_summary["ok"] = ok
    qc_summary["fail"] = fail
    save_json(root_dir / "qc_summary.json", qc_summary, dirs["tmp"])

    return RunLoopResult(
        ok=ok,
        fail=fail,
        produced_ids=produced_ids,
        qc_summary=qc_summary,
        abort_reason=abort_reason,
        root_dir=root_dir,
        run_log=run_log,
    )


def _record_failed_result(
    *,
    pid_hint: str,
    result: Dict[str, Any],
    qc_summary: Dict[str, Any],
    failed_f: Any,
    err_f: Any,
) -> None:
    err_code = "runtime/fatal"
    qc_summary["errors"][err_code] = int(qc_summary["errors"].get(err_code, 0)) + 1
    failed_f.write(f"{pid_hint} {err_code} {json.dumps(result, ensure_ascii=False)}\n")
    err_f.write(
        json.dumps(
            {
                "page_id": pid_hint,
                "err_code": err_code,
                "detail": result,
            },
            ensure_ascii=False,
        )
        + "\n"
    )


def _record_success_meta(
    *,
    pid: str,
    result: Dict[str, Any],
    qc_summary: Dict[str, Any],
    err_f: Any,
) -> None:
    meta = result.get("meta", {}) or {}

    den = str(meta.get("density_level", "normal"))
    sc = str(meta.get("scale_profile", "dpi300"))

    qc_summary["density"][den] = int(qc_summary["density"].get(den, 0)) + 1
    qc_summary["scale"][sc] = int(qc_summary["scale"].get(sc, 0)) + 1

    if bool(meta.get("has_equation", False)):
        qc_summary["math_pages"] = int(qc_summary["math_pages"]) + 1
    if bool(meta.get("has_equation_layout", False)):
        qc_summary["math_layout_pages"] = int(qc_summary["math_layout_pages"]) + 1
    if int(meta.get("mask_math_nonzero", 0) or 0) > 0:
        qc_summary["math_mask_nonempty_pages"] = int(qc_summary["math_mask_nonempty_pages"]) + 1

    rec = result.get("recovered_from") or []
    if rec:
        qc_summary["recovered"] = int(qc_summary["recovered"]) + 1
        err_f.write(
            json.dumps(
                {
                    "page_id": pid,
                    "err_code": "runtime/recovered",
                    "detail": rec,
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    if result.get("fallback_used", False):
        qc_summary["fallback_used"] = int(qc_summary["fallback_used"]) + 1
        if result.get("last_traceback"):
            err_f.write(
                json.dumps(
                    {
                        "page_id": pid,
                        "err_code": "runtime/fallback_traceback",
                        "detail": result.get("last_traceback"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def _record_future_exception(
    *,
    pid_hint: str,
    exc: BaseException,
    qc_summary: Dict[str, Any],
    failed_f: Any,
    err_f: Any,
) -> None:
    err_code = "runtime/exception"
    qc_summary["errors"][err_code] = int(qc_summary["errors"].get(err_code, 0)) + 1
    tb = traceback.format_exc()

    failed_f.write(f"{pid_hint} {err_code} {repr(exc)}\n")
    err_f.write(
        json.dumps(
            {
                "page_id": pid_hint,
                "err_code": err_code,
                "detail": repr(exc),
                "traceback": tb,
            },
            ensure_ascii=False,
        )
        + "\n"
    )