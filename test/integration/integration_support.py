from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from docsynthfab.orchestrator import RunOrchestrator


TERMINAL_STATES = {"done", "completed", "failed", "error", "cancelled"}


def wait_for_run(
    orch: RunOrchestrator,
    run_id: str,
    *,
    timeout_s: float = 90.0,
):
    deadline = time.time() + timeout_s
    last_status = None

    while time.time() < deadline:
        last_status = orch.get_status(run_id)
        state = str(getattr(last_status, "state", ""))

        if state in TERMINAL_STATES:
            return last_status

        time.sleep(0.25)

    raise TimeoutError(f"Run did not finish in {timeout_s}s. Last status={last_status!r}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_run_succeeded(status) -> None:
    assert str(getattr(status, "state", "")) in {"done", "completed"}


def assert_basic_output_tree(out_root: Path, expected_pages: int) -> None:
    assert (out_root / "images").exists()
    assert (out_root / "masks").exists()
    assert (out_root / "ann").exists()
    assert (out_root / "gt").exists()
    assert (out_root / "reports").exists()
    assert (out_root / "exports").exists()

    assert len(sorted((out_root / "images").glob("*.png"))) == expected_pages
    assert len(sorted((out_root / "ann").glob("*.json"))) == expected_pages
    assert len(sorted((out_root / "gt").glob("*.json"))) == expected_pages


def load_single_annotation(out_root: Path) -> dict[str, Any]:
    ann_files = sorted((out_root / "ann").glob("*.json"))
    assert len(ann_files) == 1
    return load_json(ann_files[0])