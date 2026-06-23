from __future__ import annotations

from pathlib import Path

import pytest

from e2e_support import default_config_path


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: end-to-end acceptance tests")
    config.addinivalue_line("markers", "slow: slow end-to-end tests")
    config.addinivalue_line("markers", "diversity: mathematical diversity acceptance tests")


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def e2e_default_config(project_root: Path) -> Path:
    return default_config_path(project_root)


@pytest.fixture
def e2e_out_root(project_root: Path) -> Path:
    out = project_root / "test_artifacts" / "e2e"
    out.mkdir(parents=True, exist_ok=True)
    return out