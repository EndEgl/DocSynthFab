# src/ai1_gen/io/exporter.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - numpy>=1.24,<3.0
# - Pillow>=10,<12

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import numpy as np
from PIL import Image


def ensure_dataset_dirs(out_root: str | Path) -> Dict[str, Path]:
    """
    Create and return the standard output directory structure for one dataset run.

    The returned dictionary is used by the generator pipeline to write images,
    masks, annotations, split files, reports, exports, and temporary files.
    """
    root = Path(out_root)

    dirs = {
        "root": root,
        "images": root / "images",
        "masks": root / "masks",
        "ann": root / "ann",
        "gt": root / "gt",
        "splits": root / "splits",
        "reports": root / "reports",
        "exports": root / "exports",
        "tmp": root / "_tmp",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return dirs


def _atomic_write_bytes(dst: str | Path, data: bytes, tmp_dir: str | Path) -> None:
    """
    Write bytes atomically by first writing to a temporary file, then replacing
    the destination path.

    This avoids partially written files when the process is interrupted during
    image or JSON export.
    """
    dst_path = Path(dst)
    tmp_path_root = Path(tmp_dir)

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path_root.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        prefix=dst_path.name + ".",
        suffix=".tmp",
        dir=str(tmp_path_root),
    )

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp_path, str(dst_path))

    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            # Cleanup should never hide the original write error.
            pass


def _to_pil_image(arr_u8: np.ndarray) -> Image.Image:
    """
    Convert a uint8 NumPy array into a Pillow image.

    Supported shapes:
    - (H, W) grayscale
    - (H, W, 3) RGB
    """
    if not isinstance(arr_u8, np.ndarray):
        raise TypeError("arr_u8 must be a numpy.ndarray")

    if arr_u8.dtype != np.uint8:
        raise TypeError(f"arr_u8 dtype must be uint8, got {arr_u8.dtype}")

    if arr_u8.ndim == 2:
        return Image.fromarray(arr_u8)

    if arr_u8.ndim == 3 and arr_u8.shape[2] == 3:
        return Image.fromarray(arr_u8)

    raise ValueError(
        f"Unsupported array shape for PNG export: {arr_u8.shape}. "
        "Expected (H, W) or (H, W, 3)."
    )


def save_png_u8(dst: str | Path, arr_u8: np.ndarray, tmp_dir: str | Path) -> None:
    """
    Save a uint8 NumPy array as PNG using an atomic write.

    The function accepts grayscale or RGB arrays and rejects unsupported shapes
    early to prevent invalid dataset files.
    """
    image = _to_pil_image(arr_u8)

    with tempfile.SpooledTemporaryFile(max_size=8_000_000) as buffer:
        image.save(buffer, format="PNG", optimize=False)
        buffer.seek(0)
        _atomic_write_bytes(dst, buffer.read(), tmp_dir)


def save_json(dst: str | Path, obj: Dict[str, Any], tmp_dir: str | Path) -> None:
    """
    Save a JSON object as UTF-8 using an atomic write.

    ensure_ascii=False is intentional so multilingual synthetic text remains
    readable in exported annotation files.
    """
    data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    _atomic_write_bytes(dst, data, tmp_dir)