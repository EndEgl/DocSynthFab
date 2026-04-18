# src/ai1_gen/io/exporter.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - Pillow>=10,<12
# - numpy>=1.24,<3.0

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

from PIL import Image
import numpy as np


def ensure_dataset_dirs(out_root: Path) -> Dict[str, Path]:
    dirs = {
        "images": out_root / "images",
        "masks": out_root / "masks",
        "ann": out_root / "ann",
        "splits": out_root / "splits",
        "gt": out_root / "gt",
        "tmp": out_root / "_tmp",
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    return dirs


def _atomic_write_bytes(dst: Path, data: bytes, tmp_dir: Path) -> None:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=dst.name + ".", suffix=".tmp", dir=str(tmp_dir))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(dst))
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def _to_pil_image(arr_u8: np.ndarray) -> Image.Image:
    """
    Pillow 10+ ile uyumlu, mode parametresi vermeden güvenli dönüşüm.
    Desteklenen girişler:
    - (H, W) uint8  -> grayscale
    - (H, W, 3) uint8 -> RGB
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


def save_png_u8(dst: Path, arr_u8: np.ndarray, tmp_dir: Path) -> None:
    img = _to_pil_image(arr_u8)
    buf = tempfile.SpooledTemporaryFile(max_size=8_000_000)
    img.save(buf, format="PNG", optimize=False)
    buf.seek(0)
    _atomic_write_bytes(dst, buf.read(), tmp_dir)


def save_json(dst: Path, obj: Dict[str, Any], tmp_dir: Path) -> None:
    data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    _atomic_write_bytes(dst, data, tmp_dir)