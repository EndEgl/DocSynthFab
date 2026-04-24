from __future__ import annotations

import json
from pathlib import Path

import pytest

import ai1_gen.cli as cli_mod


class DummyCfg:
    raw = {
        "run": {
            "fail_fast": False,
            "max_fail_ratio": 0.5,
            "jsonl_flush_batch_size": 2,
            "max_pending_mult": 1.0,
            "max_pending_min": 1,
            "worker": {
                "max_tries": 2,
                "disable_augment_on_try": 2,
                "jitter_seed_step": 1000,
                "fallback_dpi": 300,
            },
            "splits": {"train": 0.5, "val": 0.25, "test": 0.25},
        }
    }
    out_root = "out"
    pages = 4
    workers = 1
    seed = 123
    version = "ai1-ds-v1.3.2"

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


class DummyExecutor:
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
                "jsonl_line": json.dumps({"page_id": pid, "page_text": f"text-{pid}", "meta": {}}) + "\n",
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


@pytest.mark.e2e
def test_cli_outputs_consistency(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(cli_mod, "load_config", lambda _p: DummyCfg())
    monkeypatch.setattr(cli_mod.cf, "ProcessPoolExecutor", DummyExecutor)
    monkeypatch.setattr(cli_mod.cf, "wait", lambda pending, return_when=None: (set(pending), set()))

    def fake_dirs(_out_root):
        base = tmp_path / "out"
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
            "out",
            "--pages",
            "4",
            "--workers",
            "1",
            "--seed",
            "123",
        ],
    )

    cli_mod.main()

    out_root = tmp_path / "out"
    assert (out_root / "qc_summary.json").exists()
    assert (out_root / "run.log").exists()
    assert (out_root / "gt_pages.jsonl").exists()
    assert (out_root / "splits" / "train.txt").exists()
    assert (out_root / "splits" / "val.txt").exists()
    assert (out_root / "splits" / "test.txt").exists()

    qc_summary = json.loads((out_root / "qc_summary.json").read_text(encoding="utf-8"))
    assert qc_summary["ok"] == 4
    assert qc_summary["fail"] == 0

    jsonl_lines = (out_root / "gt_pages.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(jsonl_lines) == 4