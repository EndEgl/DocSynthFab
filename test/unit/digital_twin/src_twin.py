# test/unit/digital_twin/src_twin.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# Source digital twin for src/docsynthfab.
#
# This module builds a structural snapshot of the source tree:
# - Python file list
# - module names
# - content hashes
# - imports
# - __all__ exports
# - top-level constants
# - function signatures
# - class signatures and methods
#
# It uses AST parsing, not imports, for the snapshot stage.

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import os
import pkgutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


SNAPSHOT_SCHEMA_VERSION = "ai1-src-digital-twin-v1"

IGNORED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

# These modules are intentionally not imported in the broad import smoke test.
# They are entrypoints or GUI entrypoints and are tested separately.
SKIP_BROAD_IMPORT_MODULES = {
    "docsynthfab.cli.__main__",
    "docsynthfab.cli.cli",
    "docsynthfab.gui.web.app",
    "docsynthfab.gui.desktop.app",
}


@dataclass(frozen=True)
class TwinPaths:
    project_root: Path
    src_root: Path
    package_root: Path
    snapshot_path: Path


def resolve_paths() -> TwinPaths:
    """
    Expected file location:
      <project>/test/unit/digital_twin/src_twin.py
    """
    this_file = Path(__file__).resolve()

    project_root = this_file.parents[3]
    src_root = project_root / "src"
    package_root = src_root / "docsynthfab"
    snapshot_path = (
        project_root
        / "test"
        / "unit"
        / "digital_twin"
        / "src_twin_snapshot.json"
    )

    return TwinPaths(
        project_root=project_root,
        src_root=src_root,
        package_root=package_root,
        snapshot_path=snapshot_path,
    )


def ensure_src_on_path() -> None:
    paths = resolve_paths()
    src = str(paths.src_root)

    if src not in sys.path:
        sys.path.insert(0, src)


def update_requested() -> bool:
    return os.getenv("AI1_UPDATE_SRC_TWIN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def module_name_from_path(path: Path, src_root: Path) -> str:
    rel = path.relative_to(src_root)

    if rel.name == "__init__.py":
        rel = rel.parent
    else:
        rel = rel.with_suffix("")

    return ".".join(rel.parts)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iter_python_files(package_root: Path) -> list[Path]:
    files: list[Path] = []

    for path in package_root.rglob("*.py"):
        if any(part in IGNORED_DIR_NAMES for part in path.parts):
            continue
        files.append(path)

    return sorted(files)


def safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ast.dump(node)


def literal_eval_safe(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def annotation_to_str(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    return safe_unparse(node)


def default_to_str(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    return safe_unparse(node)


def function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    args = node.args

    positional_args = list(args.posonlyargs) + list(args.args)
    defaults = list(args.defaults)
    default_offset = len(positional_args) - len(defaults)

    positional: list[dict[str, Any]] = []

    for index, arg in enumerate(positional_args):
        default_node = defaults[index - default_offset] if index >= default_offset else None
        positional.append(
            {
                "name": arg.arg,
                "annotation": annotation_to_str(arg.annotation),
                "default": default_to_str(default_node),
            }
        )

    kwonly: list[dict[str, Any]] = []

    for arg, default_node in zip(args.kwonlyargs, args.kw_defaults):
        kwonly.append(
            {
                "name": arg.arg,
                "annotation": annotation_to_str(arg.annotation),
                "default": default_to_str(default_node),
            }
        )

    return {
        "kind": "async" if isinstance(node, ast.AsyncFunctionDef) else "sync",
        "name": node.name,
        "decorators": [safe_unparse(d) for d in node.decorator_list],
        "returns": annotation_to_str(node.returns),
        "positional": positional,
        "vararg": (
            {
                "name": args.vararg.arg,
                "annotation": annotation_to_str(args.vararg.annotation),
            }
            if args.vararg is not None
            else None
        ),
        "kwonly": kwonly,
        "kwarg": (
            {
                "name": args.kwarg.arg,
                "annotation": annotation_to_str(args.kwarg.annotation),
            }
            if args.kwarg is not None
            else None
        ),
    }


def extract_imports(tree: ast.Module) -> dict[str, list[str]]:
    direct_imports: list[str] = []
    from_imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                direct_imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            prefix = "." * int(node.level or 0)
            module = prefix + (node.module or "")
            imported_names = ",".join(sorted(alias.name for alias in node.names))
            from_imports.append(f"{module}:{imported_names}")

    return {
        "import": sorted(set(direct_imports)),
        "from": sorted(set(from_imports)),
    }


def extract_all_exports(tree: ast.Module) -> Optional[list[str]]:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    value = literal_eval_safe(node.value)
                    if isinstance(value, list) and all(isinstance(x, str) for x in value):
                        return sorted(value)

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "__all__" and node.value:
                value = literal_eval_safe(node.value)
                if isinstance(value, list) and all(isinstance(x, str) for x in value):
                    return sorted(value)

    return None


def extract_top_level_assignments(tree: ast.Module) -> dict[str, str]:
    """
    Capture public-ish module constants.

    Private implementation variables are ignored unless they are dunder version data.
    """
    out: dict[str, str] = {}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if name.startswith("_") and name != "__version__":
                        continue
                    out[name] = safe_unparse(node.value)

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.value is not None:
                name = node.target.id
                if name.startswith("_") and name != "__version__":
                    continue
                out[name] = safe_unparse(node.value)

    return dict(sorted(out.items()))


def extract_top_level_functions(tree: ast.Module) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = function_signature(node)

    return dict(sorted(out.items()))


def extract_class_info(node: ast.ClassDef) -> dict[str, Any]:
    fields: dict[str, Optional[str]] = {}
    class_assignments: dict[str, str] = {}
    methods: dict[str, dict[str, Any]] = {}

    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods[item.name] = function_signature(item)

        elif isinstance(item, ast.AnnAssign):
            if isinstance(item.target, ast.Name):
                fields[item.target.id] = annotation_to_str(item.annotation)

        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    class_assignments[target.id] = safe_unparse(item.value)

    return {
        "name": node.name,
        "bases": [safe_unparse(base) for base in node.bases],
        "decorators": [safe_unparse(d) for d in node.decorator_list],
        "fields": dict(sorted(fields.items())),
        "class_assignments": dict(sorted(class_assignments.items())),
        "methods": dict(sorted(methods.items())),
    }


def extract_classes(tree: ast.Module) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            out[node.name] = extract_class_info(node)

    return dict(sorted(out.items()))


def analyze_file(path: Path, *, project_root: Path, src_root: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text, filename=str(path))

    return {
        "relpath": rel_posix(path, project_root),
        "module": module_name_from_path(path, src_root),
        "sha256": sha256_text(text),
        "line_count": len(text.splitlines()),
        "imports": extract_imports(tree),
        "__all__": extract_all_exports(tree),
        "assignments": extract_top_level_assignments(tree),
        "functions": extract_top_level_functions(tree),
        "classes": extract_classes(tree),
    }


def build_src_twin_manifest() -> dict[str, Any]:
    paths = resolve_paths()

    if not paths.package_root.exists():
        raise AssertionError(f"package root not found: {paths.package_root}")

    files = iter_python_files(paths.package_root)

    modules: dict[str, dict[str, Any]] = {}

    for file_path in files:
        info = analyze_file(
            file_path,
            project_root=paths.project_root,
            src_root=paths.src_root,
        )
        modules[info["module"]] = info

    package_dirs = sorted(
        {
            rel_posix(file_path.parent, paths.project_root)
            for file_path in files
        }
    )

    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "package": "docsynthfab",
        "python_files_count": len(files),
        "package_dirs": package_dirs,
        "modules": dict(sorted(modules.items())),
    }


def write_snapshot(manifest: dict[str, Any]) -> None:
    paths = resolve_paths()
    paths.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    paths.snapshot_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_snapshot() -> dict[str, Any]:
    paths = resolve_paths()
    return json.loads(paths.snapshot_path.read_text(encoding="utf-8-sig"))


def compare_manifests(expected: dict[str, Any], current: dict[str, Any]) -> list[str]:
    diffs: list[str] = []

    if expected.get("schema_version") != current.get("schema_version"):
        diffs.append(
            f"SCHEMA_VERSION_CHANGED: {expected.get('schema_version')} -> "
            f"{current.get('schema_version')}"
        )

    if expected.get("python_files_count") != current.get("python_files_count"):
        diffs.append(
            f"PYTHON_FILE_COUNT_CHANGED: {expected.get('python_files_count')} -> "
            f"{current.get('python_files_count')}"
        )

    if expected.get("package_dirs") != current.get("package_dirs"):
        diffs.append("PACKAGE_DIRS_CHANGED")

    expected_modules = expected.get("modules", {}) or {}
    current_modules = current.get("modules", {}) or {}

    expected_names = set(expected_modules)
    current_names = set(current_modules)

    for name in sorted(expected_names - current_names):
        diffs.append(f"MISSING_MODULE: {name}")

    for name in sorted(current_names - expected_names):
        diffs.append(f"ADDED_MODULE: {name}")

    keys_to_compare = [
        "relpath",
        "sha256",
        "line_count",
        "imports",
        "__all__",
        "assignments",
        "functions",
        "classes",
    ]

    for name in sorted(expected_names & current_names):
        expected_mod = expected_modules[name]
        current_mod = current_modules[name]

        for key in keys_to_compare:
            if expected_mod.get(key) != current_mod.get(key):
                diffs.append(f"CHANGED:{name}:{key}")

    return diffs


def iter_manifest_module_names() -> list[str]:
    manifest = build_src_twin_manifest()
    return sorted(manifest["modules"].keys())


def import_all_manifest_modules() -> list[str]:
    """
    Import broad safe modules and return failures as strings.

    GUI/entrypoint modules are skipped here and tested separately.
    """
    ensure_src_on_path()

    failures: list[str] = []

    for module_name in iter_manifest_module_names():
        if module_name in SKIP_BROAD_IMPORT_MODULES:
            continue

        try:
            importlib.import_module(module_name)
        except Exception as exc:
            failures.append(f"{module_name}: {type(exc).__name__}: {exc}")

    return failures


def iter_pkgutil_module_names() -> list[str]:
    """
    Cross-check modules via pkgutil after importing docsynthfab.

    Note:
    pkgutil.walk_packages(docsynthfab.__path__, prefix="docsynthfab.")
    discovers submodules/packages, but it does not include the root package
    itself. The AST/path manifest includes src/docsynthfab/__init__.py as
    docsynthfab, so we add it explicitly.
    """
    ensure_src_on_path()

    import docsynthfab

    names: list[str] = ["docsynthfab"]

    for mod in pkgutil.walk_packages(docsynthfab.__path__, prefix="docsynthfab."):
        names.append(mod.name)

    return sorted(set(names))




