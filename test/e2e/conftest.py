# test/e2e/conftest.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9

from __future__ import annotations

from pathlib import Path

import pytest

from e2e_support import default_config_path


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def e2e_default_config(project_root: Path) -> Path:
    return default_config_path(project_root)


@pytest.fixture
def e2e_out_root() -> Path:
    """
    Persistent E2E output root.

    E2E tests write generated datasets here so outputs can be inspected
    manually after test execution.
    """
    out = Path(r"D:\ai1_test_2_100")
    out.mkdir(parents=True, exist_ok=True)
    return out