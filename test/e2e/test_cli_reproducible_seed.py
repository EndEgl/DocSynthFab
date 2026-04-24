from __future__ import annotations

import json
from pathlib import Path

import pytest

import ai1_gen.cli as cli_mod


class DummyCfg:
    def __init__(self, out_root: str):
        self.raw = {
            "run": {
                "fail_fast": False,
                "max_fail_ratio": 0.5,
                "jsonl_flush_batch_size": 10,
                "max_pending_mult": 1.0,
                "max_pending_min": 1,
                "worker": {
                    "max_tries": 2,
                    "disable_augment_on_try": 2,
                    "jitter_seed_step": 1000,
                    "fallback_dpi": 300,
                },
                "splits": {"train": 0.8, "val": 0.1, "test": 0.1},
            }
        }
        self.out_root = out_root
        self.pages = 3
        self.workers = 1
        self.seed = 777
        self.version = "ai1-ds-v1.3.2"

    def telemetry(self):
        return {
            "mode": "single_line",
            "ascii_only": True,
            "show_eta": True,
            "show_rate": True,
            "update_interval_s": 999,
            "temperature": {
                "require_temp_sensor": False,
                "prefer_gpu": True,
            },
        }


class DummyFuture:
    def __init__(self, result):
        self._result = result

    def result(self):
        return self._result

    def cancel(self):
        return None


class DeterministicExecutor:
    def __init__(self, *args, **kwargs):
        self.idx = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, args):
        idx = self.idx
        self.idx += 1
        pid = f"{idx:06d}"
        return DummyFuture(
            {
                "page_id": pid,
                "ok": True,
                "jsonl_line": json.dumps(
                    {"page_id": pid, "page_text": f"stable-{pid}", "meta": {"density_level": "normal", "scale_profile": "dpi300"}}
                ) + "\n",
                "meta": {
                    "density_level": "normal",
                    "scale_profile": "dpi300",
                    "has_equation": False,
                    "has_equation_layout": False,
                    "mask_math_nonzero": 0,
                },
                "recovered_from": [],
            }
        )


def _run_once(tmp_path, monkeypatch, out_name: str):
    monkeypatch.setattr(cli_mod, "load_config", lambda _p: DummyCfg(out_name))
    monkeypatch.setattr(cli_mod.cf, "ProcessPoolExecutor", DeterministicExecutor)
    monkeypatch.setattr(cli_mod.cf, "wait", lambda pending, return_when=None: (set(pending), set()))

    def fake_dirs(_out_root):
        base = tmp_path / out_name
        for p in [
            base,
            base / "images",
            base / "masks",
            base / "ann",
            base / "gt",
            base / "splits",
            base / "_tmp",
        ]:
            p.mkdir(parents=True, exist_ok=True)
        return {
            "root": base,
            "images": base / "images",
            "masks": base / "masks",
            "ann": base / "ann",
            "gt": base / "gt",
            "splits": base / "splits",
            "tmp": base / "_tmp",
        }

    monkeypatch.setattr(cli_mod, "ensure_dataset_dirs", fake_dirs)

    import sys
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai1_gen.cli",
            "--config",
            "configs/minimal_valid.yaml",
            "--out",
            out_name,
            "--pages",
            "3",
            "--workers",
            "1",
            "--seed",
            "777",
        ],
    )

    cli_mod.main()

    out_root = tmp_path / out_name
    return {
        "jsonl": (out_root / "gt_pages.jsonl").read_text(encoding="utf-8"),
        "train": (out_root / "splits" / "train.txt").read_text(encoding="utf-8"),
        "val": (out_root / "splits" / "val.txt").read_text(encoding="utf-8"),
        "test": (out_root / "splits" / "test.txt").read_text(encoding="utf-8"),
    }


@pytest.mark.e2e
def test_cli_reproducible_seed(tmp_path, monkeypatch):
    r1 = _run_once(tmp_path, monkeypatch, "out_a")
    r2 = _run_once(tmp_path, monkeypatch, "out_b")

    assert r1 == r2