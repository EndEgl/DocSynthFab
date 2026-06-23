# tools/scan_project_deps.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import ast
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SEARCH_ROOTS = [
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "test",
    PROJECT_ROOT / "tests",
    PROJECT_ROOT / "tools",
]

LOCAL_TOP_LEVEL = {
    "docsynthfab",
    "e2e_support",
    "acceptance_report",
    "quality_metrics",
    "integration_support",
}

TOOLS_DIR = PROJECT_ROOT / "tools"

REPORT_TXT_PATH = TOOLS_DIR / "imports_report.txt"
REPORT_MD_PATH = TOOLS_DIR / "PYTHON_DEPENDENCIES_REPORT.md"
REPORT_JSON_PATH = TOOLS_DIR / "PYTHON_DEPENDENCIES_REPORT.json"


@dataclass(frozen=True)
class ImportRecord:
    import_name: str
    kind: str
    files: List[str]


@dataclass(frozen=True)
class DistributionRecord:
    import_name: str
    distribution_name: str
    version: str
    license: str
    summary: str
    home_page: str
    project_url: str
    files: List[str]


def is_stdlib(name: str) -> bool:
    top = name.split(".")[0]
    return top in getattr(sys, "stdlib_module_names", set()) or top == "__future__"


def iter_py_files() -> list[Path]:
    files: list[Path] = []

    for root in SEARCH_ROOTS:
        if root.exists():
            files.extend(root.rglob("*.py"))

    return sorted(p for p in files if p.is_file())


def read_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")

    return text.lstrip("\ufeff")


def collect_imports() -> list[ImportRecord]:
    imports_by_name: dict[str, set[str]] = defaultdict(set)

    for path in iter_py_files():
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError as e:
            print(f"[WARN] Syntax error skipped: {path} -> {e}")
            continue

        rel = str(path.relative_to(PROJECT_ROOT))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    imports_by_name[top].add(rel)

            elif isinstance(node, ast.ImportFrom):
                # Skip relative imports like:
                # from .foo import bar
                # from ..shared.paths import x
                if node.level and node.level > 0:
                    continue

                if node.module:
                    top = node.module.split(".")[0]
                    imports_by_name[top].add(rel)


    rows: list[ImportRecord] = []

    for name, files in sorted(imports_by_name.items(), key=lambda x: x[0].lower()):
        if name in LOCAL_TOP_LEVEL:
            kind = "local"
        elif is_stdlib(name):
            kind = "stdlib"
        else:
            kind = "third_party_or_unknown"

        rows.append(
            ImportRecord(
                import_name=name,
                kind=kind,
                files=sorted(files),
            )
        )

    return rows


def safe_metadata_value(meta: metadata.PackageMetadata, key: str) -> str:
    try:
        value = meta.get(key, "")
    except Exception:
        return ""

    return str(value or "").strip()


def first_project_url(meta: metadata.PackageMetadata) -> str:
    values = []

    try:
        values = list(meta.get_all("Project-URL") or [])
    except Exception:
        values = []

    return "; ".join(str(v) for v in values[:5])


def build_packages_distributions_map() -> dict[str, list[str]]:
    try:
        return {
            key: sorted(value)
            for key, value in metadata.packages_distributions().items()
        }
    except Exception:
        return {}


def distribution_records_for_imports(import_rows: Iterable[ImportRecord]) -> list[DistributionRecord]:
    package_map = build_packages_distributions_map()
    records: list[DistributionRecord] = []

    for row in import_rows:
        if row.kind != "third_party_or_unknown":
            continue

        dist_names = package_map.get(row.import_name, [])

        if not dist_names:
            records.append(
                DistributionRecord(
                    import_name=row.import_name,
                    distribution_name="UNKNOWN",
                    version="UNKNOWN",
                    license="UNKNOWN",
                    summary="No installed distribution metadata found.",
                    home_page="",
                    project_url="",
                    files=row.files,
                )
            )
            continue

        for dist_name in dist_names:
            try:
                dist = metadata.distribution(dist_name)
                meta = dist.metadata
                version = str(dist.version or "").strip()
            except Exception:
                records.append(
                    DistributionRecord(
                        import_name=row.import_name,
                        distribution_name=dist_name,
                        version="UNKNOWN",
                        license="UNKNOWN",
                        summary="Could not read installed distribution metadata.",
                        home_page="",
                        project_url="",
                        files=row.files,
                    )
                )
                continue

            license_text = safe_metadata_value(meta, "License")
            classifier_licenses = [
                c.replace("License :: OSI Approved ::", "").strip()
                for c in (meta.get_all("Classifier") or [])
                if str(c).startswith("License ::")
            ]

            if not license_text and classifier_licenses:
                license_text = "; ".join(classifier_licenses)

            records.append(
                DistributionRecord(
                    import_name=row.import_name,
                    distribution_name=dist_name,
                    version=version or "UNKNOWN",
                    license=license_text or "UNKNOWN",
                    summary=safe_metadata_value(meta, "Summary"),
                    home_page=safe_metadata_value(meta, "Home-page"),
                    project_url=first_project_url(meta),
                    files=row.files,
                )
            )

    return sorted(
        records,
        key=lambda r: (r.distribution_name.lower(), r.import_name.lower()),
    )


def write_imports_report(import_rows: list[ImportRecord]) -> None:
    with REPORT_TXT_PATH.open("w", encoding="utf-8") as f:
        f.write("DocSynthFab Python Import Report\n")
        f.write("================================\n\n")

        f.write(f"Project root: {PROJECT_ROOT}\n")
        f.write("Search roots:\n")
        for root in SEARCH_ROOTS:
            f.write(f"  - {root.relative_to(PROJECT_ROOT) if root.exists() else root} {'[missing]' if not root.exists() else ''}\n")
        f.write("\n")

        for row in import_rows:
            f.write(f"{row.import_name}\t{row.kind}\t{len(row.files)} file(s)\n")
            for file in row.files:
                f.write(f"  - {file}\n")
            f.write("\n")


def write_python_license_md(
    import_rows: list[ImportRecord],
    dist_records: list[DistributionRecord],
) -> None:
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    with REPORT_MD_PATH.open("w", encoding="utf-8") as f:
        f.write("# DocSynthFab Python Dependencies License Report\n\n")

        f.write(
            "This report is generated from direct Python imports found in the project source tree. "
            "It uses installed Python package metadata when available.\n\n"
        )

        f.write("## Important limitations\n\n")
        f.write("- This report is not legal advice.\n")
        f.write("- It detects direct Python imports, not every transitive dependency.\n")
        f.write("- It may miss packages listed in requirements files but not imported directly.\n")
        f.write("- License fields depend on installed package metadata and may be incomplete.\n")
        f.write("- Before public release, compare this report with `requirements*.txt` and Docker dependencies.\n\n")

        f.write("## Local package names\n\n")
        for name in sorted(LOCAL_TOP_LEVEL):
            f.write(f"- `{name}`\n")
        f.write("\n")

        f.write("## Direct third-party / unknown imports\n\n")

        if not dist_records:
            f.write("No third-party imports detected.\n\n")
        else:
            f.write("| Import | Distribution | Version | License | Summary |\n")
            f.write("|---|---|---:|---|---|\n")

            for rec in dist_records:
                f.write(
                    "| "
                    f"`{rec.import_name}` | "
                    f"`{rec.distribution_name}` | "
                    f"`{rec.version}` | "
                    f"{rec.license.replace('|', '/')} | "
                    f"{rec.summary.replace('|', '/')} "
                    "|\n"
                )

            f.write("\n")

        f.write("## Usage locations\n\n")

        for rec in dist_records:
            f.write(f"### `{rec.import_name}`\n\n")
            f.write(f"- Distribution: `{rec.distribution_name}`\n")
            f.write(f"- Version: `{rec.version}`\n")
            f.write(f"- License: `{rec.license}`\n")

            if rec.home_page:
                f.write(f"- Home-page: {rec.home_page}\n")

            if rec.project_url:
                f.write(f"- Project URLs: {rec.project_url}\n")

            f.write("- Used in:\n")
            for file in rec.files:
                f.write(f"  - `{file}`\n")
            f.write("\n")

        f.write("## Standard library imports\n\n")
        stdlib_rows = [row for row in import_rows if row.kind == "stdlib"]

        for row in stdlib_rows:
            f.write(f"- `{row.import_name}`: {len(row.files)} file(s)\n")

        f.write("\n## Local imports\n\n")
        local_rows = [row for row in import_rows if row.kind == "local"]

        for row in local_rows:
            f.write(f"- `{row.import_name}`: {len(row.files)} file(s)\n")


def write_python_license_json(
    import_rows: list[ImportRecord],
    dist_records: list[DistributionRecord],
) -> None:
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "project": "DocSynthFab",
        "note": (
            "Generated from direct Python imports. "
            "This is not a complete legal SBOM and may not include transitive dependencies."
        ),
        "local_top_level": sorted(LOCAL_TOP_LEVEL),
        "imports": [asdict(row) for row in import_rows],
        "distributions": [asdict(row) for row in dist_records],
    }

    REPORT_JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def print_summary(import_rows: list[ImportRecord], dist_records: list[DistributionRecord]) -> None:
    counts: dict[str, int] = defaultdict(int)

    for row in import_rows:
        counts[row.kind] += 1

    print(f"Wrote: {REPORT_TXT_PATH}")
    print(f"Wrote: {REPORT_MD_PATH}")
    print(f"Wrote: {REPORT_JSON_PATH}")
    print()

    print("=== import kind counts ===")
    for key in ["local", "stdlib", "third_party_or_unknown"]:
        print(f"{key}: {counts.get(key, 0)}")

    print()
    print("=== third_party_or_unknown ===")
    for rec in dist_records:
        print(
            f"{rec.import_name}\t"
            f"dist={rec.distribution_name}\t"
            f"version={rec.version}\t"
            f"license={rec.license}"
        )


def main() -> int:
    import_rows = collect_imports()
    dist_records = distribution_records_for_imports(import_rows)

    write_imports_report(import_rows)
    write_python_license_md(import_rows, dist_records)
    write_python_license_json(import_rows, dist_records)
    print_summary(import_rows, dist_records)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
