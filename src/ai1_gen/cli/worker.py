# src/ai1_gen/cli/worker.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0

from __future__ import annotations

import json
import os
import random
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

from ai1_gen.augment.apply_augment import apply_augment
from ai1_gen.config import load_config
from ai1_gen.io.exporter import save_json, save_png_u8
from ai1_gen.layout.layout_sampler import sample_page_spec
from ai1_gen.qc.validators import validate_page
from ai1_gen.render.page_renderer import render_page_layers

from .fallback import make_fallback_render
from .gt_export import build_gt_export
from .metadata import attach_worker_debug_meta, sync_ann_meta_from_masks


def worker_generate_validate_save(
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

            sync_ann_meta_from_masks(ann, mt, mm)
            attach_worker_debug_meta(ann, ps, mt, mm)

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
                continue

            return _save_success_result(
                rr=rr,
                page_id=page_id,
                dirs_str=dirs_str,
                worker_tmp=worker_tmp,
                recovered_from=recovered_from,
            )

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
            continue

    return _try_fallback_result(
        cfg=cfg,
        page_id=page_id,
        dirs_str=dirs_str,
        worker_tmp=worker_tmp,
        fallback_dpi=fallback_dpi,
        recovered_from=recovered_from,
        last_err_code=last_err_code,
        last_extra=last_extra,
        last_exc=last_exc,
        last_tb=last_tb,
    )


def _save_success_result(
    *,
    rr: Dict[str, Any],
    page_id: str,
    dirs_str: Dict[str, str],
    worker_tmp: Path,
    recovered_from: list[Dict[str, Any]],
) -> Dict[str, Any]:
    ann = rr["ann"]
    mt = rr["mask_text_u8"]
    mm = rr["mask_math_u8"]
    pid = ann.get("page_id", page_id)

    _save_render_payload(pid=pid, rr=rr, mt=mt, mm=mm, ann=ann, dirs_str=dirs_str, worker_tmp=worker_tmp)

    gt_obj = build_gt_export(ann)
    save_json(Path(dirs_str["gt"]) / f"{pid}.json", gt_obj, worker_tmp)

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


def _try_fallback_result(
    *,
    cfg: Any,
    page_id: str,
    dirs_str: Dict[str, str],
    worker_tmp: Path,
    fallback_dpi: int,
    recovered_from: list[Dict[str, Any]],
    last_err_code: Optional[str],
    last_extra: Optional[Dict[str, Any]],
    last_exc: Optional[BaseException],
    last_tb: Optional[str],
) -> Dict[str, Any]:
    try:
        rr_fb = make_fallback_render(cfg, page_id=page_id, dpi=fallback_dpi)
        ann = rr_fb["ann"]
        mt = rr_fb["mask_text_u8"]
        mm = rr_fb["mask_math_u8"]

        sync_ann_meta_from_masks(ann, mt, mm)

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

        if last_err_code:
            ann["meta"]["_fallback_from_qc_code"] = last_err_code
            ann["meta"]["_fallback_from_qc_extra"] = last_extra or {}

        if last_exc is not None:
            ann["meta"]["_fallback_from_exception"] = repr(last_exc)

        result = _save_success_result(
            rr=rr_fb,
            page_id=page_id,
            dirs_str=dirs_str,
            worker_tmp=worker_tmp,
            recovered_from=recovered_from,
        )
        result["fallback_used"] = True
        result["last_traceback"] = last_tb
        return result

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


def _save_render_payload(
    *,
    pid: str,
    rr: Dict[str, Any],
    mt: np.ndarray,
    mm: np.ndarray,
    ann: Dict[str, Any],
    dirs_str: Dict[str, str],
    worker_tmp: Path,
) -> None:
    images_dir = Path(dirs_str["images"])
    masks_dir = Path(dirs_str["masks"])
    ann_dir = Path(dirs_str["ann"])

    images_dir.mkdir(parents=True, exist_ok=True)
    masks_dir.mkdir(parents=True, exist_ok=True)
    ann_dir.mkdir(parents=True, exist_ok=True)
    Path(dirs_str["gt"]).mkdir(parents=True, exist_ok=True)

    save_png_u8(images_dir / f"{pid}.png", rr["image_u8"], worker_tmp)
    save_png_u8(masks_dir / f"{pid}_mask_text.png", mt, worker_tmp)
    save_png_u8(masks_dir / f"{pid}_mask_math.png", mm, worker_tmp)
    save_json(ann_dir / f"{pid}.json", ann, worker_tmp)


_worker_generate_validate_save = worker_generate_validate_save