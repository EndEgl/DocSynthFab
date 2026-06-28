# src/docsynthfab/exporters/native.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .common import copy_existing_tree, copy_file, write_text


_NATIVE_README = """# Native Export

This folder contains the generator-native dataset package.

## Contents

- `images/`: generated page images
- `masks/`: generated text/math masks
- `ann/`: full annotation JSON files
- `gt/`: ground-truth export JSON files
- `splits/`: train/val/test page id lists
- `label_schema.json`: class and task schema

Use this format if you want maximum access to all generator metadata.
"""


def export_native(out_root: Path) -> Dict[str, Any]:
    """Copy the native dataset structure into exports/native."""
    out_root = Path(out_root)
    export_root = out_root / "exports" / "native"
    export_root.mkdir(parents=True, exist_ok=True)

    copied_dirs: List[str] = []

    for name in ("images", "masks", "ann", "gt", "splits"):
        src_dir = out_root / name
        dst_dir = export_root / name

        if copy_existing_tree(src_dir, dst_dir):
            copied_dirs.append(name)

    copy_file(out_root / "reports" / "label_schema.json", export_root / "label_schema.json")
    copy_file(out_root / "reports" / "dataset_card.md", export_root / "dataset_card.md")
    copy_file(out_root / "reports" / "run_manifest.json", export_root / "run_manifest.json")

    write_text(export_root / "README.md", _NATIVE_README)

    return {
        "target": "native",
        "export_root": str(export_root),
        "copied_dirs": copied_dirs,
    }



