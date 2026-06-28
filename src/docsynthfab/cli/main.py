# src/docsynthfab/cli/main.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .args import normalize_export_targets, parse_cli_args
from .reports_exports import write_exports_safely, write_reports_safely
from .run_loop import run_generation_loop
from .splits import split_of


def main(argv: Sequence[str] | None = None) -> None:
    import docsynthfab.cli as cli_pkg

    args = parse_cli_args(argv)

    cfg = cli_pkg.load_config(args.config)
    run_cfg = (cfg.raw.get("run", {}) or {}) if hasattr(cfg, "raw") else {}

    export_targets = normalize_export_targets(run_cfg, args.export)

    out_root = Path(args.out) if args.out else Path(cfg.out_root)
    out_root = Path(str(out_root))
    out_root.mkdir(parents=True, exist_ok=True)

    dirs = cli_pkg.ensure_dataset_dirs(out_root)

    for key in ("images", "masks", "ann", "gt", "splits", "reports", "exports", "tmp"):
        if key in dirs:
            Path(dirs[key]).mkdir(parents=True, exist_ok=True)

    total = int(args.pages) if args.pages and args.pages > 0 else int(cfg.pages)
    workers = int(args.workers) if args.workers and args.workers > 0 else int(cfg.workers)
    seed = int(args.seed) if args.seed >= 0 else int(cfg.seed)

    if total <= 0:
        raise SystemExit("run/invalid-pages")

    if workers <= 0:
        workers = 1

    result = run_generation_loop(
        cfg=cfg,
        cfg_path=str(Path(args.config).resolve()),
        dirs=dirs,
        total=total,
        workers=workers,
        seed=seed,
        run_cfg=run_cfg,
    )

    produced_ids_sorted = sorted(result.produced_ids)

    train: list[str] = []
    val: list[str] = []
    test: list[str] = []

    n_ok = len(produced_ids_sorted)

    for i, pid in enumerate(produced_ids_sorted):
        split_name = split_of(i, n_ok, run_cfg)
        if split_name == "train":
            train.append(pid)
        elif split_name == "val":
            val.append(pid)
        else:
            test.append(pid)

    Path(dirs["splits"]).mkdir(parents=True, exist_ok=True)

    (dirs["splits"] / "train.txt").write_text("\n".join(train) + ("\n" if train else ""), encoding="utf-8")
    (dirs["splits"] / "val.txt").write_text("\n".join(val) + ("\n" if val else ""), encoding="utf-8")
    (dirs["splits"] / "test.txt").write_text("\n".join(test) + ("\n" if test else ""), encoding="utf-8")

    write_reports_safely(
        run_log=result.run_log,
        out_root=result.root_dir,
        cfg_raw=cfg.raw if hasattr(cfg, "raw") else {},
        cfg_path=str(Path(args.config).resolve()),
        version=getattr(cfg, "version", "0.1.0"),
        pages_requested=total,
        pages_ok=result.ok,
        pages_fail=result.fail,
        seed=seed,
        workers=workers,
        splits={
            "train": len(train),
            "val": len(val),
            "test": len(test),
        },
        qc_summary=result.qc_summary,
        export_targets=export_targets,
    )

    write_exports_safely(
        run_log=result.run_log,
        out_root=result.root_dir,
        export_targets=export_targets,
    )

    with result.run_log.open("a", encoding="utf-8") as f:
        f.write(
            f"done total={total} ok={result.ok} fail={result.fail} seed={seed} "
            f"workers={workers} abort_reason={result.abort_reason} "
            f"math_pages={result.qc_summary['math_pages']} "
            f"math_mask_nonempty_pages={result.qc_summary['math_mask_nonempty_pages']}\n"
        )

    if result.abort_reason is not None:
        raise SystemExit(result.abort_reason)


if __name__ == "__main__":
    main()



