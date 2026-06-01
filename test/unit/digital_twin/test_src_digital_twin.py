# test/unit/digital_twin/test_src_digital_twin.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9

from __future__ import annotations

import importlib

import pytest

from .src_twin import (
    build_src_twin_manifest,
    compare_manifests,
    import_all_manifest_modules,
    iter_manifest_module_names,
    iter_pkgutil_module_names,
    read_snapshot,
    resolve_paths,
    update_requested,
    write_snapshot,
)


def test_src_digital_twin_snapshot_matches_current_src():
    """
    Strict source digital twin.

    First baseline creation:
      set PYTHONPATH=%CD%\\src
      set AI1_UPDATE_SRC_TWIN=1
      python -m pytest test/unit/digital_twin -q
      set AI1_UPDATE_SRC_TWIN=

    Normal validation:
      python -m pytest test/unit/digital_twin -q
    """
    paths = resolve_paths()
    current = build_src_twin_manifest()

    if update_requested():
        write_snapshot(current)
        pytest.skip(f"updated src digital twin snapshot: {paths.snapshot_path}")

    if not paths.snapshot_path.exists():
        pytest.fail(
            "missing src digital twin snapshot.\n"
            "Create it with CMD:\n"
            "  set PYTHONPATH=%CD%\\src\n"
            "  set AI1_UPDATE_SRC_TWIN=1\n"
            "  python -m pytest test/unit/digital_twin -q\n"
            "  set AI1_UPDATE_SRC_TWIN="
        )

    expected = read_snapshot()
    diffs = compare_manifests(expected, current)

    assert not diffs, (
        "src digital twin mismatch.\n"
        "If this source change is intentional, update the snapshot with CMD:\n"
        "  set PYTHONPATH=%CD%\\src\n"
        "  set AI1_UPDATE_SRC_TWIN=1\n"
        "  python -m pytest test/unit/digital_twin -q\n"
        "  set AI1_UPDATE_SRC_TWIN=\n\n"
        "Diffs:\n"
        + "\n".join(diffs[:500])
    )


def test_src_twin_module_discovery_matches_pkgutil():
    """
    AST/path-based manifest and Python package discovery should agree.
    """
    manifest_modules = set(iter_manifest_module_names())
    pkgutil_modules = set(iter_pkgutil_module_names())

    missing_from_pkgutil = sorted(manifest_modules - pkgutil_modules)
    missing_from_manifest = sorted(pkgutil_modules - manifest_modules)

    assert not missing_from_pkgutil, (
        "Modules exist on disk but pkgutil cannot discover them:\n"
        + "\n".join(missing_from_pkgutil)
    )

    assert not missing_from_manifest, (
        "pkgutil discovers modules not present in manifest:\n"
        + "\n".join(missing_from_manifest)
    )


def test_every_safe_src_module_imports_without_error():
    """
    Runtime import twin.

    This catches:
    - broken moved imports
    - missing dependency imports
    - relative import mistakes
    - old compatibility imports that were not updated
    """
    failures = import_all_manifest_modules()

    assert not failures, "\n".join(failures)


def test_cli_package_contract():
    """
    CLI is now a package:
      src/ai1_gen/cli/
    Old top-level:
      src/ai1_gen/cli.py
    should not exist anymore.
    """
    paths = resolve_paths()

    old_cli = paths.package_root / "cli.py"
    cli_dir = paths.package_root / "cli"

    assert cli_dir.exists() and cli_dir.is_dir()
    assert (cli_dir / "__init__.py").exists()
    assert (cli_dir / "__main__.py").exists()
    assert (cli_dir / "cli.py").exists()
    assert (cli_dir / "main.py").exists()

    assert not old_cli.exists(), (
        "Old src/ai1_gen/cli.py still exists. "
        "It conflicts with the new ai1_gen.cli package."
    )

def test_config_package_contract():
    """
    Config is now a package:
      src/ai1_gen/config/

    Old top-level:
      src/ai1_gen/config.py

    should not exist anymore.
    """
    paths = resolve_paths()

    old_config = paths.package_root / "config.py"
    config_dir = paths.package_root / "config"

    assert config_dir.exists() and config_dir.is_dir()
    assert (config_dir / "__init__.py").exists()
    assert (config_dir / "config.py").exists()
    assert (config_dir / "loader.py").exists()
    assert (config_dir / "helpers.py").exists()
    assert (config_dir / "errors.py").exists()

    assert not old_config.exists(), (
        "Old src/ai1_gen/config.py still exists. "
        "It conflicts with the new ai1_gen.config package."
    )


def test_config_backward_compat_exports():
    """
    Existing code still depends on:
      from ai1_gen.config import load_config, ConfigError

    Keep this public contract stable after modularization.
    """
    import ai1_gen.config as config

    required = [
        "AppConfig",
        "ConfigError",
        "load_config",
        "_get",
        "_norm_dist",
        "get_nested",
        "normalize_distribution",
    ]

    for name in required:
        assert hasattr(config, name), f"ai1_gen.config missing export: {name}"

    assert "load_config" in config.__all__
    assert "ConfigError" in config.__all__
    assert "AppConfig" in config.__all__

def test_cli_backward_compat_exports():
    """
    Old unit tests and external users may still import private compatibility names
    from ai1_gen.cli. Keep them until tests are fully migrated.
    """
    import ai1_gen.cli as cli

    required = [
        "main",
        "_build_gt_export",
        "_make_fallback_render",
        "_normalized_split_ratios",
        "_split_of",
        "_worker_generate_validate_save",
    ]

    for name in required:
        assert hasattr(cli, name), f"ai1_gen.cli missing compatibility export: {name}"


def test_modular_gui_layout_contract():
    """
    Modular GUI target contract.
    """
    paths = resolve_paths()
    root = paths.package_root

    expected_files = [
        root / "gui" / "__init__.py",
        root / "gui" / "shared" / "__init__.py",
        root / "gui" / "shared" / "paths.py",
        root / "gui" / "shared" / "override_utils.py",
        root / "gui" / "shared" / "upload_utils.py",
        root / "gui" / "web" / "__init__.py",
        root / "gui" / "web" / "app.py",
        root / "gui" / "web" / "state.py",
        root / "gui" / "web" / "presets.py",
        root / "gui" / "web" / "config_preview.py",
        root / "gui" / "web" / "content_actions.py",
        root / "gui" / "web" / "live_events.py",
        root / "gui" / "web" / "run_state.py",
        root / "gui" / "web" / "template_csv.py",
        root / "gui" / "desktop" / "__init__.py",
        root / "gui" / "desktop" / "app.py",
    ]

    missing = [str(path) for path in expected_files if not path.exists()]
    assert not missing, "Missing expected modular GUI files:\n" + "\n".join(missing)


def test_old_web_gui_is_removed_or_launcher_only():
    """
    Final target:
    - old src/ai1_gen/web_gui.py should be removed, OR
    - if kept temporarily, it must be a tiny launcher only.
    """
    paths = resolve_paths()
    old_web_gui = paths.package_root / "web_gui.py"

    if not old_web_gui.exists():
        return

    text = old_web_gui.read_text(encoding="utf-8")

    assert "from nicegui import ui" not in text
    assert "RunOrchestrator()" not in text
    assert (
        "ai1_gen.gui.web.app" in text
        or "runpy.run_module" in text
    ), "web_gui.py exists but does not look like a clean launcher."


def test_no_duplicate_shared_runtime_state():
    """
    Intermediate duplicate state file should not remain in the final target.

    Web runtime owner:
      ai1_gen.gui.web.state.WEB_STATE
    """
    paths = resolve_paths()
    duplicate = paths.package_root / "gui" / "shared" / "runtime_state.py"

    assert not duplicate.exists(), (
        "Duplicate state file still exists: "
        f"{duplicate}\n"
        "Final target should use ai1_gen.gui.web.state.WEB_STATE."
    )


def test_latex_normalize_backward_compat_contract():
    """
    Older render modules may still import normalize_latex_expr from miktex_render.
    Keep this compatibility unless every old import has been removed.
    """
    from ai1_gen.latex.miktex_render import normalize_latex_expr

    assert normalize_latex_expr("sum_{i=1}^{n} i") == r"\sum_{i=1}^{n} i"
    assert normalize_latex_expr("sqrt{x+1}") == r"\sqrt{x+1}"
    assert normalize_latex_expr("frac{a}{b}") == r"\frac{a}{b}"


def test_orchestrator_gui_contract():
    """
    GUI depends on these orchestrator methods.
    """
    from ai1_gen.orchestrator import RunOrchestrator

    orch = RunOrchestrator()

    for method_name in [
        "start",
        "cancel",
        "get_status",
        "get_summary",
        "get_schema_for_ui",
        "build_effective_config_yaml_text",
        "build_config_with_user_override",
    ]:
        assert hasattr(orch, method_name), f"RunOrchestrator missing: {method_name}"
        assert callable(getattr(orch, method_name))

    schema = orch.get_schema_for_ui()
    assert isinstance(schema, list)
    assert schema

    first = schema[0]
    assert isinstance(first, dict)
    assert {"key", "label", "field_type"} <= set(first.keys())


def test_gui_entrypoints_import_when_dependencies_are_available():
    """
    Import GUI entrypoints explicitly.

    If optional GUI deps are missing on a minimal CI machine, these are skipped.
    On your local dev machine they should normally run.
    """
    pytest.importorskip("nicegui")
    importlib.import_module("ai1_gen.gui.web.app")

    pytest.importorskip("PySide6")
    importlib.import_module("ai1_gen.gui.desktop.app")