# src/ai1_gen/cli/args.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import argparse
from typing import Any, Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai1-gen")
    parser.add_argument("--config", required=True, help="configs/default.yaml")
    parser.add_argument("--out", default="", help="Output root override (default config io.out_root)")
    parser.add_argument("--pages", type=int, default=0, help="Total pages override")
    parser.add_argument("--workers", type=int, default=0, help="Workers override")
    parser.add_argument("--seed", type=int, default=-1, help="Seed override")
    parser.add_argument(
        "--export",
        default="",
        help="Comma-separated export targets override: native,segformer,coco",
    )
    return parser


def parse_cli_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def normalize_export_targets(run_cfg: dict[str, Any], raw_export: str = "") -> list[str]:
    raw_export = str(raw_export or "").strip()

    if raw_export:
        targets = [x.strip().lower() for x in raw_export.split(",") if x.strip()]
    else:
        cfg_export = run_cfg.get("export_targets", ["native", "segformer", "coco"])

        if isinstance(cfg_export, str):
            targets = [x.strip().lower() for x in cfg_export.split(",") if x.strip()]
        elif isinstance(cfg_export, list):
            targets = [str(x).strip().lower() for x in cfg_export if str(x).strip()]
        else:
            targets = ["native", "segformer", "coco"]

    return targets or ["native"]