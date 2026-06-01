# test/integration/conftest.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - numpy>=1.24,<3.0
# - PyYAML>=6.0,<7.0

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import pytest

from ai1_gen.orchestrator import RunOrchestrator, RunRequest


TERMINAL_STATES = {"done", "completed", "failed", "error", "cancelled"}


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def default_config_path(project_root: Path) -> Path:
    path = project_root / "configs" / "default.yaml"
    assert path.exists(), f"default config not found: {path}"
    return path


@pytest.fixture
def integration_out_root(tmp_path: Path) -> Path:
    out = tmp_path / "integration_out"
    out.mkdir(parents=True, exist_ok=True)
    return out


@pytest.fixture
def unicode_samples() -> dict[str, str]:
    return {
        "turkish": "İstanbul ölçü ğüşiöç Türkçe karakter testi",
        "cyrillic": "Пример текста на кириллице",
        "greek": "Παράδειγμα κειμένου στα ελληνικά",
        "symbols": "± × ÷ ≤ ≥ √ ∑ ∞",
        "mixed": "İstanbul Пример Παράδειγμα ± √",
    }


@pytest.fixture
def run_orchestrator() -> RunOrchestrator:
    return RunOrchestrator()


@pytest.fixture
def make_run_request(
    default_config_path: Path,
    integration_out_root: Path,
) -> Callable[..., RunRequest]:
    def _make(
        *,
        out_name: str = "run",
        pages: int = 1,
        workers: int = 1,
        seed: int = 123,
        smoke_test: bool = False,
        overrides: dict[str, Any] | None = None,
    ) -> RunRequest:
        return RunRequest(
            config_path=str(default_config_path),
            out_root=str(integration_out_root / out_name),
            pages=pages,
            workers=workers,
            seed=seed,
            smoke_test=smoke_test,
            overrides=overrides or {},
        )

    return _make


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


def assert_basic_output_tree(out_root: Path, expected_pages: int) -> None:
    assert (out_root / "images").exists()
    assert (out_root / "ann").exists()
    assert (out_root / "gt").exists()

    image_files = sorted((out_root / "images").glob("*.png"))
    ann_files = sorted((out_root / "ann").glob("*.json"))
    gt_files = sorted((out_root / "gt").glob("*.json"))

    assert len(image_files) == expected_pages
    assert len(ann_files) == expected_pages
    assert len(gt_files) == expected_pages