# src/docsynthfab/gui/shared/font_status.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional


EXPECTED_FONT_DIRS: List[str] = [
    "latin",
    "mono",
    "cyrillic",
    "greek",
    "arabic",
    "hebrew",
    "devanagari",
    "cjk",
    "hangul",
    "thai",
    "symbols",
    "decorative",
    "handwriting",
]


FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}


@dataclass(frozen=True)
class FontDirStatus:
    name: str
    exists: bool
    file_count: int
    path: str

    @property
    def ok(self) -> bool:
        return bool(self.exists and self.file_count > 0)


@dataclass(frozen=True)
class FontSetupStatus:
    fonts_root: str
    fonts_root_exists: bool
    dirs: List[FontDirStatus]
    manifest_exists: bool
    manifest_path: str
    licenses_dir_exists: bool
    licenses_dir_path: str
    license_file_count: int

    @property
    def ok(self) -> bool:
        required_dirs_ok = all(item.ok for item in self.dirs)
        return bool(
            self.fonts_root_exists
            and required_dirs_ok
            and self.manifest_exists
            and self.licenses_dir_exists
            and self.license_file_count > 0
        )

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["ok"] = self.ok
        return data


def project_root_from_file() -> Path:
    """
    Resolve the project root from this file.

    Current file:
      src/docsynthfab/gui/shared/font_status.py

    Project root:
      docsynthfab/
    """
    return Path(__file__).resolve().parents[4]


def default_fonts_root() -> Path:
    return project_root_from_file() / "assets" / "fonts"


def _count_font_files(folder: Path) -> int:
    if not folder.exists() or not folder.is_dir():
        return 0

    count = 0

    for item in folder.iterdir():
        if item.is_file() and item.suffix.lower() in FONT_EXTENSIONS:
            count += 1

    return count


def _count_license_files(folder: Path) -> int:
    if not folder.exists() or not folder.is_dir():
        return 0

    count = 0

    for item in folder.iterdir():
        if not item.is_file():
            continue

        name = item.name.lower()

        if (
            "license" in name
            or "licence" in name
            or "ofl" in name
            or item.suffix.lower() in {".txt", ".md", ".json"}
        ):
            count += 1

    return count


def inspect_font_setup(
    fonts_root: Optional[str | Path] = None,
    *,
    expected_dirs: Optional[List[str]] = None,
) -> FontSetupStatus:
    root = Path(fonts_root) if fonts_root is not None else default_fonts_root()
    root = root.resolve()

    names = expected_dirs or EXPECTED_FONT_DIRS

    dir_statuses: List[FontDirStatus] = []

    for name in names:
        folder = root / name
        exists = folder.exists() and folder.is_dir()
        file_count = _count_font_files(folder)

        dir_statuses.append(
            FontDirStatus(
                name=str(name),
                exists=bool(exists),
                file_count=int(file_count),
                path=str(folder),
            )
        )

    manifest_path = root / "FONT_MANIFEST.json"
    licenses_dir_path = root / "LICENSES"

    return FontSetupStatus(
        fonts_root=str(root),
        fonts_root_exists=bool(root.exists() and root.is_dir()),
        dirs=dir_statuses,
        manifest_exists=bool(manifest_path.exists() and manifest_path.is_file()),
        manifest_path=str(manifest_path),
        licenses_dir_exists=bool(licenses_dir_path.exists() and licenses_dir_path.is_dir()),
        licenses_dir_path=str(licenses_dir_path),
        license_file_count=int(_count_license_files(licenses_dir_path)),
    )


def format_font_status_text(status: FontSetupStatus) -> str:
    lines: List[str] = []

    root_mark = "OK" if status.fonts_root_exists else "MISSING"
    lines.append(f"Fonts root: {root_mark}")
    lines.append(status.fonts_root)
    lines.append("")

    lines.append("Font directories:")

    for item in status.dirs:
        if item.ok:
            mark = "OK"
        elif item.exists:
            mark = "EMPTY"
        else:
            mark = "MISSING"

        lines.append(f"- {item.name}: {mark} ({item.file_count} font files)")

    lines.append("")

    manifest_mark = "OK" if status.manifest_exists else "MISSING"
    licenses_mark = "OK" if status.licenses_dir_exists else "MISSING"

    lines.append(f"FONT_MANIFEST.json: {manifest_mark}")
    lines.append(f"LICENSES directory: {licenses_mark}")
    lines.append(f"License files: {status.license_file_count}")

    lines.append("")

    if status.ok:
        lines.append("Overall: OK")
    else:
        lines.append("Overall: needs attention")

    return "\n".join(lines)


def missing_font_items(status: FontSetupStatus) -> List[str]:
    missing: List[str] = []

    if not status.fonts_root_exists:
        missing.append("assets/fonts root")

    for item in status.dirs:
        if not item.exists:
            missing.append(f"{item.name}/ directory")
        elif item.file_count <= 0:
            missing.append(f"{item.name}/ font files")

    if not status.manifest_exists:
        missing.append("FONT_MANIFEST.json")

    if not status.licenses_dir_exists:
        missing.append("LICENSES/ directory")
    elif status.license_file_count <= 0:
        missing.append("LICENSES files")

    return missing


def fonts_root_path_text(fonts_root: Optional[str | Path] = None) -> str:
    root = Path(fonts_root) if fonts_root is not None else default_fonts_root()
    return str(root.resolve())



