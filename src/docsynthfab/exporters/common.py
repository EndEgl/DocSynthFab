# src/docsynthfab/exporters/common.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List


def read_json(path: Path) -> Dict[str, Any]:
    """Read a UTF-8 JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    """Write a UTF-8 JSON file with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text and ensure a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def copy_file(src: Path, dst: Path) -> bool:
    """Copy a file if it exists. Return True when copied."""
    if not src.exists():
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def reset_dir(path: Path) -> None:
    """Remove and recreate an export directory."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_existing_tree(src_dir: Path, dst_dir: Path) -> bool:
    """Copy a directory tree if the source exists."""
    if dst_dir.exists():
        shutil.rmtree(dst_dir)

    if not src_dir.exists():
        return False

    shutil.copytree(src_dir, dst_dir)
    return True


def read_split_ids(splits_dir: Path, split: str) -> List[str]:
    """Read page ids from splits/train.txt, val.txt, or test.txt."""
    path = splits_dir / f"{split}.txt"

    if not path.exists():
        return []

    return [
        item.strip()
        for item in path.read_text(encoding="utf-8").splitlines()
        if item.strip()
    ]


def all_split_ids(out_root: Path) -> Dict[str, List[str]]:
    """Read all train/val/test split ids from an output directory."""
    splits_dir = out_root / "splits"

    return {
        "train": read_split_ids(splits_dir, "train"),
        "val": read_split_ids(splits_dir, "val"),
        "test": read_split_ids(splits_dir, "test"),
    }



