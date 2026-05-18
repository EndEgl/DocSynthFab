# tools/import_list.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOTS = [
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "test",
    PROJECT_ROOT / "tests",
]

LOCAL_TOP_LEVEL = {
    "ai1_gen",
}


def is_stdlib(name: str) -> bool:
    top = name.split(".")[0]
    return top in getattr(sys, "stdlib_module_names", set()) or top == "__future__"


def iter_py_files() -> list[Path]:
    files: list[Path] = []
    for root in SEARCH_ROOTS:
        if root.exists():
            files.extend(root.rglob("*.py"))
    return sorted(files)


def main() -> int:
    imports_by_name: dict[str, set[str]] = defaultdict(set)

    for path in iter_py_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except SyntaxError as e:
            print(f"[WARN] Syntax error skipped: {path} -> {e}")
            continue

        rel = path.relative_to(PROJECT_ROOT)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    imports_by_name[top].add(str(rel))

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    imports_by_name[top].add(str(rel))

    rows = []
    for name, files in sorted(imports_by_name.items(), key=lambda x: x[0].lower()):
        if name in LOCAL_TOP_LEVEL:
            kind = "local"
        elif is_stdlib(name):
            kind = "stdlib"
        else:
            kind = "third_party_or_unknown"

        rows.append((name, kind, sorted(files)))

    out = PROJECT_ROOT / "imports_report.txt"

    with out.open("w", encoding="utf-8") as f:
        for name, kind, files in rows:
            f.write(f"{name}\t{kind}\t{len(files)} file(s)\n")
            for file in files:
                f.write(f"  - {file}\n")
            f.write("\n")

    print(f"Wrote: {out}")
    print("\n=== third_party_or_unknown ===")
    for name, kind, files in rows:
        if kind == "third_party_or_unknown":
            print(f"{name}\t{len(files)} file(s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())