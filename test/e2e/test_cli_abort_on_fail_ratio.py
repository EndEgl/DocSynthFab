from __future__ import annotations

import sys
from pathlib import Path

import pytest

import ai1_gen.cli as cli_mod


class DummyFuture:
    def __init__(self, result):
        self._result = result

    def result(self):
        return self._result

    def cancel(self):
        return None


class DummyExecutor:
    def __init__(self, *args, **kwargs):
        self.calls = 0
        self._futures = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, args):
        self.calls += 1
        fut = DummyFuture(
            {
                "page_id": f"{self.calls:06d}",
                "ok": False,
                "jsonl_line": "",
                "meta": {},
                "fatal": True,
                "recovered_from": [],
            }
        )
        self._futures.append(fut)
        return fut


class DummyCfg:
    raw = {
        "run": {
            "fail_fast": False,
            "max_fail_ratio": 0.01,
            "jsonl_flush_batch_size": 2,
            "max_pending_mult": 1.0,
            "max_pending_min": 1,
            "worker": {
                "max_tries": 2,
                "disable_augment_on_try": 2,
                "jitter_seed_step": 1000,
                "fallback_dpi": 300,
            },
        }
    }
    out_root = "out"
    pages = 2
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


@pytest.mark.e2e
def test_cli_abort_on_fail_ratio(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(cli_mod, "load_config", lambda _p: DummyCfg())
    monkeypatch.setattr(cli_mod.cf, "ProcessPoolExecutor", DummyExecutor)
    monkeypatch.setattr(cli_mod.cf, "wait", lambda pending, return_when=None: (set(pending), set()))
    monkeypatch.setattr(
        cli_mod,
        "ensure_dataset_dirs",
        lambda out_root: {
            "root": tmp_path / "out",
            "images": tmp_path / "out" / "images",
            "masks": tmp_path / "out" / "masks",
            "ann": tmp_path / "out" / "ann",
            "gt": tmp_path / "out" / "gt",
            "splits": tmp_path / "out" / "splits",
            "tmp": tmp_path / "out" / "_tmp",
        },
    )

    argv = [
        "ai1_gen.cli",
        "--config",
        "configs/minimal_valid.yaml",
        "--out",
        "out",
        "--pages",
        "2",
        "--workers",
        "1",
        "--seed",
        "123",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc:
        cli_mod.main()

    assert "run/max-fail-ratio-exceeded" in str(exc.value)