# src/ai1_gen/cli.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - PyYAML>=6.0,<7.0
# - tqdm>=4.66,<5.0 (opsiyonel; burada kullanılmıyor)

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import random
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

from ai1_gen.augment.apply_augment import apply_augment
from ai1_gen.config import load_config
from ai1_gen.io.exporter import ensure_dataset_dirs, save_json, save_png_u8
from ai1_gen.layout.layout_sampler import sample_page_spec
from ai1_gen.qc.validators import validate_page
from ai1_gen.render.page_renderer import render_page_layers
from ai1_gen.telemetry.progress import ProgressPrinter, TemperatureReader, TelemetryError


# ----------------------------
# Meta sync / debug helpers
# ----------------------------
def _sync_ann_meta_from_masks(ann: Dict[str, Any], mt: np.ndarray, mm: np.ndarray) -> None:
    meta = ann.setdefault("meta", {})
    lines = ann.get("lines", []) or []
    blocks = ann.get("blocks", []) or []

    math_line_count = sum(1 for ln in lines if str(ln.get("line_type", "")) == "math")
    eq_block_count = sum(1 for b in blocks if str(b.get("block_type", "")) == "equation")
    table_block_count = sum(1 for b in blocks if str(b.get("block_type", "")) == "table")
    figure_block_count = sum(1 for b in blocks if str(b.get("block_type", "")) == "figure")

    mask_text_nonzero = int(np.count_nonzero(mt))
    mask_math_nonzero = int(np.count_nonzero(mm))

    meta["mask_text_nonzero"] = mask_text_nonzero
    meta["mask_math_nonzero"] = mask_math_nonzero
    meta["math_line_count"] = int(math_line_count)
    meta["equation_block_count"] = int(eq_block_count)
    meta["table_block_count"] = int(table_block_count)
    meta["figure_block_count"] = int(figure_block_count)

    meta["has_equation_layout"] = bool(math_line_count > 0 or eq_block_count > 0)
    meta["has_equation"] = bool((math_line_count > 0 or eq_block_count > 0) and mask_math_nonzero > 0)
    meta["has_table"] = bool(table_block_count > 0)
    meta["has_figure"] = bool(figure_block_count > 0)

    meta.setdefault("page_family", "report")

def _attach_worker_debug_meta(
    ann: Dict[str, Any],
    ps: Any,
    mt: np.ndarray,
    mm: np.ndarray,
) -> None:
    meta = ann.setdefault("meta", {})
    ps_blocks = getattr(ps, "blocks", []) or []
    ps_lines = getattr(ps, "lines", []) or []

    meta["_worker_debug"] = {
        "ps_equation_blocks": int(sum(1 for b in ps_blocks if getattr(b, "block_type", "") == "equation")),
        "ps_table_blocks": int(sum(1 for b in ps_blocks if getattr(b, "block_type", "") == "table")),
        "ps_figure_blocks": int(sum(1 for b in ps_blocks if getattr(b, "block_type", "") == "figure")),
        "ps_math_lines": int(sum(1 for ln in ps_lines if getattr(ln, "line_type", "") == "math")),
        "ps_total_lines": int(len(ps_lines)),
        "mask_text_nonzero_pre_qc": int(np.count_nonzero(mt)),
        "mask_math_nonzero_pre_qc": int(np.count_nonzero(mm)),
    }


# ----------------------------
# GT EXPORT
# ----------------------------
def _build_gt_export(ann: Dict[str, Any]) -> Dict[str, Any]:
    meta = ann.get("meta", {}) or {}
    size = ann.get("size", {}) or {}

    lines_out = []
    for ln in ann.get("lines", []) or []:
        item = {
            "line_id": int(ln.get("line_id", -1)),
            "block_id": int(ln.get("block_id", -1)),
            "line_type": str(ln.get("line_type", "")),
            "global_line_order": int(ln.get("global_line_order", -1)),
            "bbox": ln.get("bbox", [0, 0, 0, 0]),
        }
        if "gt_text" in ln:
            item["text"] = ln.get("gt_text", "")
            item["script"] = ln.get("gt_script", "unknown")
        if "gt_latex" in ln:
            item["latex"] = ln.get("gt_latex", "")
        lines_out.append(item)

    page_text = ann.get("gt_page_text", "")
    if not page_text:
        ordered = sorted(
            [(x.get("global_line_order", 0), x.get("text", "")) for x in lines_out if x.get("text")],
            key=lambda t: int(t[0]),
        )
        page_text = "\n".join(t for _, t in ordered).strip()

    return {
        "version": ann.get("version", "ai1-ds-v1.3.2"),
        "page_id": ann.get("page_id", ""),
        "size": {
            "w": int(size.get("w", 0)),
            "h": int(size.get("h", 0)),
            "dpi": int(size.get("dpi", 0)),
        },
        "meta": {
            "layout_type": meta.get("layout_type", None),
            "density_level": meta.get("density_level", None),
            "scale_profile": meta.get("scale_profile", None),
            "noise_level": meta.get("noise_level", None),
            "page_family": meta.get("page_family", None),
            "_fallback": meta.get("_fallback", False),
            "has_table": meta.get("has_table", None),
            "has_equation": meta.get("has_equation", None),
            "has_equation_layout": meta.get("has_equation_layout", None),
            "has_figure": meta.get("has_figure", None),
            "mask_text_nonzero": meta.get("mask_text_nonzero", None),
            "mask_math_nonzero": meta.get("mask_math_nonzero", None),
            "math_line_count": meta.get("math_line_count", None),
            "equation_block_count": meta.get("equation_block_count", None),
        },
        "lines": lines_out,
        "page_text": page_text,
        "gt_stats": ann.get("gt_stats", {}),
    }


def _normalized_split_ratios(run_cfg: Dict[str, Any]) -> Tuple[float, float, float]:
    splits = run_cfg.get("splits", {}) or {}
    tr = float(splits.get("train", 0.80))
    va = float(splits.get("val", 0.10))
    te = float(splits.get("test", 0.10))

    s = tr + va + te
    if s <= 0:
        return 0.80, 0.10, 0.10
    return tr / s, va / s, te / s


def _split_of(i: int, n: int, run_cfg: Dict[str, Any]) -> str:
    train_r, val_r, _ = _normalized_split_ratios(run_cfg)
    r = i / max(1, n)
    if r < train_r:
        return "train"
    if r < train_r + val_r:
        return "val"
    return "test"


# ----------------------------
# FALLBACK (son çare)
# ----------------------------
def _make_fallback_render(cfg: Any, page_id: str, dpi: int = 300) -> Dict[str, Any]:
    if dpi >= 300:
        w, h = 2481, 3507
        scale_profile = "dpi300"
    else:
        w, h = 1654, 2339
        scale_profile = "dpi200"

    page_cfg = (cfg.raw.get("page", {}) or {}) if hasattr(cfg, "raw") else {}
    bg_color = page_cfg.get("bg_color_rgb", [255, 255, 255]) or [255, 255, 255]
    bg = tuple(int(x) for x in bg_color[:3])

    img = np.full((h, w, 3), bg, dtype=np.uint8)
    mt = np.zeros((h, w), dtype=np.uint8)
    mm = np.zeros((h, w), dtype=np.uint8)

    x0, y0 = 120, 180
    x1, y1 = x0 + 140, y0 + 140
    mt[y0:y1, x0:x1] = 255
    img[y0:y1, x0:x1, :] = 0

    ann: Dict[str, Any] = {
        "version": getattr(cfg, "version", "ai1-ds-v1.3.2"),
        "page_id": page_id,
        "size": {"w": int(w), "h": int(h), "dpi": int(dpi)},
        "meta": {
            "layout_type": "single_col",
            "density_level": "sparse",
            "scale_profile": scale_profile,
            "noise_level": "clean",
            "has_table": False,
            "has_equation": False,
            "has_figure": False,
            "_fallback": True,
        },
        "gt_page_text": "FALLBACK_PAGE",
        "lines": [
            {
                "line_id": 0,
                "block_id": 0,
                "line_type": "text",
                "line_order_in_block": 0,
                "global_line_order": 0,
                "bbox": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)],
                "quad": None,
                "is_hard": False,
                "gt_text": "FALLBACK_PAGE",
                "gt_script": "latin",
            }
        ],
        "blocks": [],
        "gt_stats": {},
    }

    _sync_ann_meta_from_masks(ann, mt, mm)

    return {
        "image_u8": img,
        "mask_text_u8": mt,
        "mask_math_u8": mm,
        "ann": ann,
    }


# ----------------------------
# WORKER
# ----------------------------
def _worker_generate_validate_save(
    args: Tuple[int, str, int, str, Dict[str, str], Dict[str, Any]]
) -> Dict[str, Any]:
    idx, page_id, base_seed, cfg_path, dirs_str, options = args

    cfg = load_config(cfg_path)

    tmp_root = Path(dirs_str["tmp"])
    worker_tmp = tmp_root / f"w{os.getpid()}"
    worker_tmp.mkdir(parents=True, exist_ok=True)

    max_tries = int(options.get("max_tries", 4))
    disable_augment_on_try = int(options.get("disable_augment_on_try", 2))
    jitter_seed_step = int(options.get("jitter_seed_step", 10_000_019))
    fallback_dpi = int(options.get("fallback_dpi", 300))

    recovered_from: list[Dict[str, Any]] = []

    rr: Optional[Dict[str, Any]] = None
    last_exc: Optional[BaseException] = None
    last_tb: Optional[str] = None
    last_err_code: Optional[str] = None
    last_extra: Optional[Dict[str, Any]] = None

    for attempt in range(1, max_tries + 1):
        try:
            rng = random.Random(base_seed + idx * jitter_seed_step + attempt * 1_000_003)

            ps = sample_page_spec(cfg, rng, idx, page_id)
            rr = render_page_layers(ps, cfg, rng)

            aug_cfg = cfg.augment()
            if bool(aug_cfg.get("enable", True)) and attempt < disable_augment_on_try:
                meta = rr["ann"]["meta"]
                ar = apply_augment(
                    rr["image_u8"],
                    rr["mask_text_u8"],
                    rr["mask_math_u8"],
                    rr["ann"],
                    meta,
                    aug_cfg,
                    rng,
                )
                rr["image_u8"] = ar.image_aug_u8
                rr["mask_text_u8"] = ar.mask_text_aug_u8
                rr["mask_math_u8"] = ar.mask_math_aug_u8
                rr["ann"] = ar.ann_aug
                rr["ann"]["meta"]["aug_trace"] = ar.aug_trace
            else:
                rr["ann"]["meta"]["aug_trace"] = rr["ann"]["meta"].get("aug_trace", [])
                rr["ann"]["meta"]["_augment_disabled_by_retry"] = bool(aug_cfg.get("enable", True))

            ann = rr["ann"]
            mt = rr["mask_text_u8"]
            mm = rr["mask_math_u8"]

            _sync_ann_meta_from_masks(ann, mt, mm)
            _attach_worker_debug_meta(ann, ps, mt, mm)

            good, code, extra = validate_page(ann, mt, mm, cfg)
            if not good:
                last_err_code = code
                last_extra = extra if isinstance(extra, dict) else {"extra": extra}
                recovered_from.append(
                    {
                        "attempt": attempt,
                        "kind": "qc_fail",
                        "code": code,
                        "extra": last_extra,
                        "debug": {
                            "mask_text_nonzero": int(np.count_nonzero(mt)),
                            "mask_math_nonzero": int(np.count_nonzero(mm)),
                            "math_line_count": int(ann.get("meta", {}).get("math_line_count", 0)),
                            "equation_block_count": int(ann.get("meta", {}).get("equation_block_count", 0)),
                        },
                    }
                )
                rr = None
                continue

            pid = ann.get("page_id", page_id)

            images_dir = Path(dirs_str["images"])
            masks_dir = Path(dirs_str["masks"])
            ann_dir = Path(dirs_str["ann"])
            gt_dir = Path(dirs_str["gt"])

            images_dir.mkdir(parents=True, exist_ok=True)
            masks_dir.mkdir(parents=True, exist_ok=True)
            ann_dir.mkdir(parents=True, exist_ok=True)
            gt_dir.mkdir(parents=True, exist_ok=True)

            save_png_u8(images_dir / f"{pid}.png", rr["image_u8"], worker_tmp)
            save_png_u8(masks_dir / f"{pid}_mask_text.png", mt, worker_tmp)
            save_png_u8(masks_dir / f"{pid}_mask_math.png", mm, worker_tmp)
            save_json(ann_dir / f"{pid}.json", ann, worker_tmp)

            gt_obj = _build_gt_export(ann)
            save_json(gt_dir / f"{pid}.json", gt_obj, worker_tmp)

            jsonl_line = json.dumps(
                {
                    "page_id": pid,
                    "page_text": gt_obj.get("page_text", ""),
                    "meta": gt_obj.get("meta", {}),
                },
                ensure_ascii=False,
            ) + "\n"

            return {
                "page_id": pid,
                "ok": True,
                "jsonl_line": jsonl_line,
                "meta": gt_obj.get("meta", {}),
                "recovered_from": recovered_from,
            }

        except Exception as e:
            last_exc = e
            last_tb = traceback.format_exc()
            recovered_from.append(
                {
                    "attempt": attempt,
                    "kind": "exception",
                    "exc": repr(e),
                }
            )
            rr = None
            continue

    try:
        rr_fb = _make_fallback_render(cfg, page_id=page_id, dpi=fallback_dpi)
        ann = rr_fb["ann"]
        mt = rr_fb["mask_text_u8"]
        mm = rr_fb["mask_math_u8"]

        _sync_ann_meta_from_masks(ann, mt, mm)

        good, code, extra = validate_page(ann, mt, mm, cfg)
        if not good:
            return {
                "page_id": page_id,
                "ok": False,
                "jsonl_line": "",
                "meta": {},
                "recovered_from": recovered_from
                + [
                    {
                        "attempt": "fallback",
                        "kind": "qc_fail",
                        "code": code,
                        "extra": extra,
                    }
                ],
                "fatal": True,
            }

        pid = ann.get("page_id", page_id)

        images_dir = Path(dirs_str["images"])
        masks_dir = Path(dirs_str["masks"])
        ann_dir = Path(dirs_str["ann"])
        gt_dir = Path(dirs_str["gt"])

        images_dir.mkdir(parents=True, exist_ok=True)
        masks_dir.mkdir(parents=True, exist_ok=True)
        ann_dir.mkdir(parents=True, exist_ok=True)
        gt_dir.mkdir(parents=True, exist_ok=True)

        if last_err_code:
            ann["meta"]["_fallback_from_qc_code"] = last_err_code
            ann["meta"]["_fallback_from_qc_extra"] = last_extra or {}
        if last_exc is not None:
            ann["meta"]["_fallback_from_exception"] = repr(last_exc)

        save_png_u8(images_dir / f"{pid}.png", rr_fb["image_u8"], worker_tmp)
        save_png_u8(masks_dir / f"{pid}_mask_text.png", mt, worker_tmp)
        save_png_u8(masks_dir / f"{pid}_mask_math.png", mm, worker_tmp)
        save_json(ann_dir / f"{pid}.json", ann, worker_tmp)

        gt_obj = _build_gt_export(ann)
        save_json(gt_dir / f"{pid}.json", gt_obj, worker_tmp)

        jsonl_line = json.dumps(
            {
                "page_id": pid,
                "page_text": gt_obj.get("page_text", ""),
                "meta": gt_obj.get("meta", {}),
            },
            ensure_ascii=False,
        ) + "\n"

        return {
            "page_id": pid,
            "ok": True,
            "jsonl_line": jsonl_line,
            "meta": gt_obj.get("meta", {}),
            "recovered_from": recovered_from,
            "fallback_used": True,
            "last_traceback": last_tb,
        }

    except Exception as e2:
        return {
            "page_id": page_id,
            "ok": False,
            "jsonl_line": "",
            "meta": {},
            "recovered_from": recovered_from
            + [
                {
                    "attempt": "fallback",
                    "kind": "exception",
                    "exc": repr(e2),
                }
            ],
            "fatal": True,
            "last_traceback": traceback.format_exc(),
        }


# ----------------------------
# MAIN
# ----------------------------
def main() -> None:
    ap = argparse.ArgumentParser(prog="ai1-gen")
    ap.add_argument("--config", required=True, help="configs/default.yaml")
    ap.add_argument("--out", default="", help="Output root override (default config io.out_root)")
    ap.add_argument("--pages", type=int, default=0, help="Total pages override")
    ap.add_argument("--workers", type=int, default=0, help="Workers override")
    ap.add_argument("--seed", type=int, default=-1, help="Seed override")
    args = ap.parse_args()

    cfg = load_config(args.config)
    run_cfg = (cfg.raw.get("run", {}) or {}) if hasattr(cfg, "raw") else {}

    out_root = Path(args.out) if args.out else Path(cfg.out_root)
    out_root = Path(str(out_root))
    dirs = ensure_dataset_dirs(out_root)

    total = int(args.pages) if args.pages and args.pages > 0 else int(cfg.pages)
    workers = int(args.workers) if args.workers and args.workers > 0 else int(cfg.workers)
    seed = int(args.seed) if args.seed >= 0 else int(cfg.seed)

    if total <= 0:
        raise SystemExit("run/invalid-pages")
    if workers <= 0:
        workers = 1

    fail_fast = bool(run_cfg.get("fail_fast", False))
    max_fail_ratio = float(run_cfg.get("max_fail_ratio", 0.02))

    tel = cfg.telemetry()
    tel_temp_require = bool(tel.get("temperature", {}).get("require_temp_sensor", True))
    tel_show_eta = bool(tel.get("show_eta", True))
    tel_show_rate = bool(tel.get("show_rate", True))

    pp = ProgressPrinter(
        mode=str(tel.get("mode", "single_line")),
        ascii_only=bool(tel.get("ascii_only", True)),
    )
    temp_reader = TemperatureReader(
        require=tel_temp_require,
        prefer_gpu=bool(tel.get("temperature", {}).get("prefer_gpu", True)),
        throttle_s=float(tel.get("update_interval_s", 1.2)),
    )

    page_ids = [f"{i:06d}" for i in range(total)]

    ok = 0
    fail = 0
    start = time.time()
    last_tick = 0.0
    abort_reason: Optional[str] = None

    qc_summary: Dict[str, Any] = {
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

    failed_log = out_root / "failed_pages.log"
    errors_jsonl = out_root / "errors.jsonl"
    run_log = out_root / "run.log"
    gt_jsonl_path = out_root / "gt_pages.jsonl"

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

    failed_log.parent.mkdir(parents=True, exist_ok=True)

    with (
        failed_log.open("a", encoding="utf-8") as failed_f,
        errors_jsonl.open("a", encoding="utf-8") as err_f,
        gt_jsonl_path.open("w", encoding="utf-8") as gt_f,
        cf.ProcessPoolExecutor(max_workers=workers) as ex,
    ):
        pending: set[cf.Future] = set()
        fut_to_pid: dict[cf.Future, str] = {}

        it = iter(enumerate(page_ids))

        for _ in range(min(max_pending, total)):
            idx, pid = next(it)
            fut = ex.submit(
                _worker_generate_validate_save,
                (idx, pid, seed, str(Path(args.config).resolve()), dirs_str, worker_options),
            )
            pending.add(fut)
            fut_to_pid[fut] = pid

        done_count = 0

        while pending and abort_reason is None:
            done, pending = cf.wait(pending, return_when=cf.FIRST_COMPLETED)

            for fut in done:
                done_count += 1
                pid_hint = fut_to_pid.pop(fut, "?")

                try:
                    res = fut.result()

                    if not res.get("ok", False):
                        fail += 1
                        err_code = "runtime/fatal"
                        qc_summary["errors"][err_code] = int(qc_summary["errors"].get(err_code, 0)) + 1
                        failed_f.write(f"{pid_hint} {err_code} {json.dumps(res, ensure_ascii=False)}\n")
                        err_f.write(
                            json.dumps(
                                {
                                    "page_id": pid_hint,
                                    "err_code": err_code,
                                    "detail": res,
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
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

                        meta = res.get("meta", {}) or {}
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

                        rec = res.get("recovered_from") or []
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

                        if res.get("fallback_used", False):
                            qc_summary["fallback_used"] = int(qc_summary["fallback_used"]) + 1
                            if res.get("last_traceback"):
                                err_f.write(
                                    json.dumps(
                                        {
                                            "page_id": pid,
                                            "err_code": "runtime/fallback_traceback",
                                            "detail": res.get("last_traceback"),
                                        },
                                        ensure_ascii=False,
                                    )
                                    + "\n"
                                )

                except Exception as e:
                    fail += 1
                    err_code = "runtime/exception"
                    qc_summary["errors"][err_code] = int(qc_summary["errors"].get(err_code, 0)) + 1
                    tb = traceback.format_exc()
                    failed_f.write(f"{pid_hint} {err_code} {repr(e)}\n")
                    err_f.write(
                        json.dumps(
                            {
                                "page_id": pid_hint,
                                "err_code": err_code,
                                "detail": repr(e),
                                "traceback": tb,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
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
                    done_pages = ok + fail
                    pct = 100.0 * done_pages / float(total)
                    elapsed = max(1e-6, now - start)
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
                        if tel_temp_require:
                            raise SystemExit("telemetry/no-temp-sensor")

                    tstamp = time.strftime("%H:%M:%S")
                    parts = [
                        f"[{tstamp}] pages {done_pages:04d}/{total} ({pct:5.2f}%)",
                        f"ok {ok}",
                        f"fail {fail}",
                        f"math {qc_summary['math_pages']}",
                        f"mathmask {qc_summary['math_mask_nonempty_pages']}",
                    ]
                    if tel_show_rate:
                        parts.append(f"rate {rate:.2f}/s")
                    if tel_show_eta:
                        parts.append(f"eta {hh:02d}:{mm_:02d}:{ss:02d}")
                    parts.append(f"temp gpu={tg} cpu={tc}")
                    pp.print_line(" | ".join(parts))

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
                        _worker_generate_validate_save,
                        (idx, pid, seed, str(Path(args.config).resolve()), dirs_str, worker_options),
                    )
                    pending.add(nf)
                    fut_to_pid[nf] = pid

        if jsonl_buffer:
            gt_f.writelines(jsonl_buffer)
            gt_f.flush()
            jsonl_buffer.clear()

    pp.finish()

    produced_ids_sorted = sorted(produced_ids)

    train: list[str] = []
    val: list[str] = []
    test: list[str] = []

    n_ok = len(produced_ids_sorted)
    for i, pid in enumerate(produced_ids_sorted):
        s = _split_of(i, n_ok, run_cfg)
        if s == "train":
            train.append(pid)
        elif s == "val":
            val.append(pid)
        else:
            test.append(pid)

    (dirs["splits"] / "train.txt").write_text("\n".join(train) + ("\n" if train else ""), encoding="utf-8")
    (dirs["splits"] / "val.txt").write_text("\n".join(val) + ("\n" if val else ""), encoding="utf-8")
    (dirs["splits"] / "test.txt").write_text("\n".join(test) + ("\n" if test else ""), encoding="utf-8")

    qc_summary["ok"] = ok
    qc_summary["fail"] = fail
    save_json(out_root / "qc_summary.json", qc_summary, dirs["tmp"])

    with run_log.open("a", encoding="utf-8") as f:
        f.write(
            f"done total={total} ok={ok} fail={fail} seed={seed} "
            f"workers={workers} abort_reason={abort_reason} "
            f"math_pages={qc_summary['math_pages']} "
            f"math_mask_nonempty_pages={qc_summary['math_mask_nonempty_pages']}\n"
        )

    if abort_reason is not None:
        raise SystemExit(abort_reason)


if __name__ == "__main__":
    main()

# CMD:
# set PYTHONPATH=%CD%\src
# python -m ai1_gen.cli --config configs/default.yaml --pages 100 --workers 4