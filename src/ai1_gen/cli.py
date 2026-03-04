# src/ai1_gen/cli.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - PyYAML>=6.0,<7.0
# - tqdm>=4.66,<5.0 (opsiyonel; burada kullanılmıyor)

from __future__ import annotations

import argparse
import json
import time
import random
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

from ai1_gen.config import load_config, ConfigError
from ai1_gen.layout.layout_sampler import sample_page_spec
from ai1_gen.render.page_renderer import render_page_layers
from ai1_gen.augment.apply_augment import apply_augment
from ai1_gen.qc.validators import validate_page
from ai1_gen.io.exporter import ensure_dataset_dirs, save_png_u8, save_json
from ai1_gen.telemetry.progress import TemperatureReader, ProgressPrinter, TelemetryError


def _build_gt_export(ann: Dict[str, Any]) -> Dict[str, Any]:
    """
    OCR fail-safe için: sadece metin/latex odaklı GT export.
    ann içindeki gt_text/gt_script/gt_latex alanlarını kullanır.
    """
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
        # text
        if "gt_text" in ln:
            item["text"] = ln.get("gt_text", "")
            item["script"] = ln.get("gt_script", "unknown")
        # math
        if "gt_latex" in ln:
            item["latex"] = ln.get("gt_latex", "")
        lines_out.append(item)

    # page_text: ann.gt_page_text varsa onu al, yoksa line textlerden üret
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
        "size": {"w": int(size.get("w", 0)), "h": int(size.get("h", 0)), "dpi": int(size.get("dpi", 0))},
        "meta": {
            "layout_type": meta.get("layout_type", None),
            "density_level": meta.get("density_level", None),
            "scale_profile": meta.get("scale_profile", None),
            "noise_level": meta.get("noise_level", None),
            "has_table": meta.get("has_table", None),
            "has_equation": meta.get("has_equation", None),
            "has_figure": meta.get("has_figure", None),
        },
        "lines": lines_out,
        "page_text": page_text,
        "gt_stats": ann.get("gt_stats", {}),
    }


def _split_of(i: int, n: int) -> str:
    # deterministic: 80/10/10
    r = i / max(1, n)
    if r < 0.80:
        return "train"
    if r < 0.90:
        return "val"
    return "test"


def _worker_generate_one(args: Tuple[int, str, int, str, Dict[str, Any]]) -> Dict[str, Any]:
    # IMPORTANT: worker stdout yasak -> print yok
    idx, page_id, base_seed, cfg_path, overrides = args
    cfg = load_config(cfg_path)
    # override runtime (out burada kullanılmıyor; sadece spec ve gen)
    rng = random.Random(base_seed + idx * 10_000_019)

    ps = sample_page_spec(cfg, rng, idx, page_id)
    rr = render_page_layers(ps, cfg, rng)

    # augment
    aug_cfg = cfg.augment()
    if bool(aug_cfg.get("enable", True)):
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
    return rr


def main() -> None:
    ap = argparse.ArgumentParser(prog="ai1-gen")
    ap.add_argument("--config", required=True, help="configs/default.yaml")
    ap.add_argument("--out", default="", help="Output root override (default config io.out_root)")
    ap.add_argument("--pages", type=int, default=0, help="Total pages override")
    ap.add_argument("--workers", type=int, default=0, help="Workers override")
    ap.add_argument("--seed", type=int, default=-1, help="Seed override")
    args = ap.parse_args()

    cfg = load_config(args.config)

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

    # telemetry
    tel = cfg.telemetry()
    pp = ProgressPrinter(mode=str(tel.get("mode", "single_line")), ascii_only=bool(tel.get("ascii_only", True)))
    temp_reader = TemperatureReader(
        require=bool(tel.get("temperature", {}).get("require_temp_sensor", True)),
        prefer_gpu=bool(tel.get("temperature", {}).get("prefer_gpu", True)),
        throttle_s=float(tel.get("update_interval_s", 1.2)),
    )

    # page ids
    page_ids = [f"{i:06d}" for i in range(total)]

    ok = 0
    fail = 0
    start = time.time()
    last_tick = 0.0
    qc_summary: Dict[str, Any] = {
        "version": cfg.version,
        "total": total,
        "ok": 0,
        "fail": 0,
        "errors": {},
        "density": {},
        "scale": {},
    }

    failed_log = out_root / "failed_pages.log"
    run_log = out_root / "run.log"

    # Multiprocessing
    import concurrent.futures as cf

    ok_ids: list[str] = []

    gt_jsonl_path = out_root / "gt_pages.jsonl"
    # jsonl'i bir kere aç
    with gt_jsonl_path.open("a", encoding="utf-8") as gt_f, cf.ProcessPoolExecutor(max_workers=workers) as ex:
        futs = []
        fut_to_pid: dict[cf.Future, str] = {}

        cfg_abs = str(Path(args.config).resolve())

        for idx, pid in enumerate(page_ids):
            fut = ex.submit(_worker_generate_one, (idx, pid, seed, cfg_abs, {}))
            futs.append(fut)
            fut_to_pid[fut] = pid

        # consume
        for i, fut in enumerate(cf.as_completed(futs), start=1):
            pid_hint = fut_to_pid.get(fut, "?")
            try:
                rr = fut.result()
                ann = rr["ann"]
                mt = rr["mask_text_u8"]
                mm = rr["mask_math_u8"]

                good, code, extra = validate_page(ann, mt, mm, cfg)
                if not good:
                    fail += 1
                    qc_summary["errors"][code] = int(qc_summary["errors"].get(code, 0)) + 1
                    with failed_log.open("a", encoding="utf-8") as f:
                        f.write(f"{ann.get('page_id', pid_hint)} {code} {json.dumps(extra, ensure_ascii=False)}\n")
                    continue

                # save artifacts
                pid = ann["page_id"]
                save_png_u8(dirs["images"] / f"{pid}.png", rr["image_u8"], dirs["tmp"])
                save_png_u8(dirs["masks"] / f"{pid}_mask_text.png", mt, dirs["tmp"])
                save_png_u8(dirs["masks"] / f"{pid}_mask_math.png", mm, dirs["tmp"])
                save_json(dirs["ann"] / f"{pid}.json", ann, dirs["tmp"])

                # GT export
                gt_obj = _build_gt_export(ann)
                save_json(dirs["gt"] / f"{pid}.json", gt_obj, dirs["tmp"])

                # jsonl (tek dosya, tek handle)
                gt_f.write(json.dumps(
                    {"page_id": pid, "page_text": gt_obj.get("page_text", ""), "meta": gt_obj.get("meta", {})},
                    ensure_ascii=False
                ) + "\n")

                ok += 1
                ok_ids.append(pid)

                # dist counters
                den = str(ann["meta"].get("density_level", "normal"))
                sc = str(ann["meta"].get("scale_profile", "dpi300"))
                qc_summary["density"][den] = int(qc_summary["density"].get(den, 0)) + 1
                qc_summary["scale"][sc] = int(qc_summary["scale"].get(sc, 0)) + 1

            except Exception as e:
                # GÜVENLİK DÜZELTMESİ: Worker çökerse (örn: KeyError) program kapanmasın, bunu fail olarak kaydetsin
                fail += 1
                err_code = "runtime/exception"
                qc_summary["errors"][err_code] = int(qc_summary["errors"].get(err_code, 0)) + 1
                with failed_log.open("a", encoding="utf-8") as f:
                    f.write(f"{pid_hint} {err_code} {repr(e)}\n")
                # Hata durumunda detaylı traceback görmek istersen (sadece debug için):
                # traceback.print_exc()

            # progress tick (aynı kalsın)
            now = time.time()
            if now - last_tick >= float(tel.get("update_interval_s", 1.2)) or i == total:
                last_tick = now
                done = ok + fail
                pct = 100.0 * done / float(total)
                elapsed = max(1e-6, now - start)
                rate = done / elapsed
                eta_s = int((total - done) / max(1e-6, rate))
                hh = eta_s // 3600
                mm_ = (eta_s % 3600) // 60
                ss = eta_s % 60

                try:
                    tr = temp_reader.read()
                    tg = f"{tr.gpu_c}C" if tr.gpu_c is not None else "NA"
                    tc = f"{tr.cpu_c}C" if tr.cpu_c is not None else "NA"
                except TelemetryError:
                    raise SystemExit("telemetry/no-temp-sensor")

                tstamp = time.strftime("%H:%M:%S")
                line = (f"[{tstamp}] pages {done:04d}/{total} ({pct:5.2f}%) | "
                        f"ok {ok} fail {fail} | eta {hh:02d}:{mm_:02d}:{ss:02d} | "
                        f"temp gpu={tg} cpu={tc}")
                pp.print_line(line)

    pp.finish()

    # splits: sadece OK sayfalar
    ok_ids_sorted = sorted(ok_ids)  # "000123" string olduğu için sıralama düzgün

    train: list[str] = []
    val: list[str] = []
    test: list[str] = []

    n_ok = len(ok_ids_sorted)
    for i, pid in enumerate(ok_ids_sorted):
        s = _split_of(i, n_ok)
        if s == "train":
            train.append(pid)
        elif s == "val":
            val.append(pid)
        else:
            test.append(pid)

    (dirs["splits"] / "train.txt").write_text("\n".join(train) + "\n", encoding="utf-8")
    (dirs["splits"] / "val.txt").write_text("\n".join(val) + "\n", encoding="utf-8")
    (dirs["splits"] / "test.txt").write_text("\n".join(test) + "\n", encoding="utf-8")
    
    
    qc_summary["ok"] = ok
    qc_summary["fail"] = fail
    save_json(out_root / "qc_summary.json", qc_summary, dirs["tmp"])

    with run_log.open("a", encoding="utf-8") as f:
        f.write(f"done total={total} ok={ok} fail={fail} seed={seed} workers={workers}\n")


if __name__ == "__main__":
    main()