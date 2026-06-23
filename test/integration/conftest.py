from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pytest

from docsynthfab.orchestrator import RunOrchestrator, RunRequest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "slow: slow integration tests")


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
        export_targets: list[str] | None = None,
        overrides: dict[str, Any] | None = None,
        raw_yaml_override_text: str | None = None,
    ) -> RunRequest:
        return RunRequest(
            config_path=str(default_config_path),
            out_root=str(integration_out_root / out_name),
            pages=pages,
            workers=workers,
            seed=seed,
            smoke_test=smoke_test,
            export_targets=export_targets or ["native"],
            overrides=overrides or {},
            raw_yaml_override_text=raw_yaml_override_text,
        )

    return _make