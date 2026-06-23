# test/unit/digital_twin/test_architecture_test_coverage_twin.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9

from __future__ import annotations

from pathlib import Path


def test_architecture_contract_tests_exist():
    """
    Digital twin guard:

    These tests protect the GUI → RunRequest → Orchestrator → effective_config
    and GUI error visibility architecture. If they are renamed or deleted
    intentionally, this guard must be updated together with the architecture
    decision.
    """
    root = Path(__file__).resolve().parents[3]

    required = [
        root / "test" / "unit" / "gui" / "test_web_start_run_request_contract.py",
        root / "test" / "unit" / "gui" / "test_web_run_lifecycle_contract.py",
        root / "test" / "unit" / "gui" / "test_web_error_visibility_contract.py",
        root / "test" / "integration" / "test_architecture_gui_backend_config_contract.py",
        root / "test" / "e2e" / "test_09_backend_parameter_reaches_output_e2e.py",
    ]

    missing = [str(path.relative_to(root)) for path in required if not path.exists()]

    assert not missing, (
        "Missing architecture/digital-twin contract tests:\n"
        + "\n".join(missing)
    )



