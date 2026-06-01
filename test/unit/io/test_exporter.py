from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ai1_gen.io.exporter import (
    _atomic_write_bytes,
    _to_pil_image,
    ensure_dataset_dirs,
    save_json,
    save_png_u8,
)


# ======================================================================================
# ensure_dataset_dirs
# ======================================================================================

def test_ensure_dataset_dirs_creates_expected_relative_tree(tmp_path):
    out_root = tmp_path / "relative_out"

    dirs = ensure_dataset_dirs(out_root)

    expected = {
        "root",
        "images",
        "masks",
        "ann",
        "gt",
        "splits",
        "reports",
        "exports",
        "tmp",
    }

    assert expected.issubset(dirs.keys())

    for key in expected:
        assert Path(dirs[key]).exists(), key
        assert Path(dirs[key]).is_dir(), key


def test_ensure_dataset_dirs_returns_paths_under_root(tmp_path):
    out_root = tmp_path / "dataset_out"

    dirs = ensure_dataset_dirs(out_root)

    assert dirs["root"] == out_root
    assert dirs["images"] == out_root / "images"
    assert dirs["masks"] == out_root / "masks"
    assert dirs["ann"] == out_root / "ann"
    assert dirs["gt"] == out_root / "gt"
    assert dirs["splits"] == out_root / "splits"
    assert dirs["reports"] == out_root / "reports"
    assert dirs["exports"] == out_root / "exports"
    assert dirs["tmp"] == out_root / "_tmp"


# ======================================================================================
# _atomic_write_bytes
# ======================================================================================

def test_atomic_write_bytes_writes_payload_to_nested_target(tmp_path):
    target = tmp_path / "nested" / "dir" / "file.bin"
    tmp_dir = tmp_path / "_tmp"
    payload = b"abc123"

    _atomic_write_bytes(target, payload, tmp_dir)

    assert target.exists()
    assert target.read_bytes() == payload


def test_atomic_write_bytes_overwrites_existing_target(tmp_path):
    target = tmp_path / "nested" / "file.bin"
    tmp_dir = tmp_path / "_tmp"

    _atomic_write_bytes(target, b"old", tmp_dir)
    _atomic_write_bytes(target, b"new", tmp_dir)

    assert target.read_bytes() == b"new"


def test_atomic_write_bytes_leaves_no_tmp_file_after_success(tmp_path):
    target = tmp_path / "file.bin"
    tmp_dir = tmp_path / "_tmp"

    _atomic_write_bytes(target, b"payload", tmp_dir)

    leftovers = list(tmp_dir.glob("*.tmp"))
    assert leftovers == []


# ======================================================================================
# _to_pil_image
# ======================================================================================

def test_to_pil_image_accepts_grayscale_uint8():
    arr = np.zeros((16, 32), dtype=np.uint8)

    img = _to_pil_image(arr)

    assert isinstance(img, Image.Image)
    assert img.size == (32, 16)


def test_to_pil_image_accepts_rgb_uint8():
    arr = np.zeros((16, 32, 3), dtype=np.uint8)

    img = _to_pil_image(arr)

    assert isinstance(img, Image.Image)
    assert img.size == (32, 16)


def test_to_pil_image_rejects_non_numpy_input():
    with pytest.raises(TypeError):
        _to_pil_image([[0, 1], [2, 3]])  # type: ignore[arg-type]


def test_to_pil_image_rejects_non_uint8_array():
    arr = np.zeros((16, 32, 3), dtype=np.float32)

    with pytest.raises(TypeError):
        _to_pil_image(arr)


def test_to_pil_image_rejects_invalid_shape():
    arr = np.zeros((16, 32, 2), dtype=np.uint8)

    with pytest.raises(ValueError):
        _to_pil_image(arr)


# ======================================================================================
# save_json
# ======================================================================================

def test_save_json_writes_file_atomically(tmp_path):
    target = tmp_path / "ann" / "sample.json"
    tmp_dir = tmp_path / "_tmp"

    data = {"page_id": "000001", "ok": True}
    save_json(target, data, tmp_dir)

    assert target.exists()

    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == data


def test_save_json_overwrites_existing_file(tmp_path):
    target = tmp_path / "ann" / "sample.json"
    tmp_dir = tmp_path / "_tmp"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{"old": true}', encoding="utf-8")

    save_json(target, {"new": True}, tmp_dir)

    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == {"new": True}


def test_save_json_preserves_utf8_characters(tmp_path):
    target = tmp_path / "ann" / "utf8.json"
    tmp_dir = tmp_path / "_tmp"

    data = {
        "tr": "İstanbul, ölçü, ğüşiöç",
        "ru": "Привет",
        "el": "Καλημέρα",
        "ar": "مرحبا",
    }

    save_json(target, data, tmp_dir)

    text = target.read_text(encoding="utf-8")
    loaded = json.loads(text)

    assert loaded == data
    assert "İstanbul" in text
    assert "Привет" in text


# ======================================================================================
# save_png_u8
# ======================================================================================

def test_save_png_u8_writes_rgb_png(tmp_path):
    target = tmp_path / "images" / "page.png"
    tmp_dir = tmp_path / "_tmp"

    img = np.full((32, 64, 3), 255, dtype=np.uint8)
    save_png_u8(target, img, tmp_dir)

    assert target.exists()

    with Image.open(target) as loaded:
        assert loaded.size == (64, 32)


def test_save_png_u8_writes_grayscale_png(tmp_path):
    target = tmp_path / "masks" / "mask.png"
    tmp_dir = tmp_path / "_tmp"

    img = np.zeros((32, 64), dtype=np.uint8)
    img[0:5, 0:5] = 255

    save_png_u8(target, img, tmp_dir)

    assert target.exists()

    with Image.open(target) as loaded:
        assert loaded.size == (64, 32)


def test_save_png_u8_overwrites_existing_png(tmp_path):
    target = tmp_path / "images" / "page.png"
    tmp_dir = tmp_path / "_tmp"

    first = np.zeros((16, 16, 3), dtype=np.uint8)
    second = np.full((16, 16, 3), 255, dtype=np.uint8)

    save_png_u8(target, first, tmp_dir)
    save_png_u8(target, second, tmp_dir)

    with Image.open(target) as loaded:
        arr = np.asarray(loaded)

    assert arr.shape == (16, 16, 3)
    assert int(arr.mean()) == 255


def test_save_png_u8_rejects_non_uint8_input(tmp_path):
    target = tmp_path / "bad.png"
    tmp_dir = tmp_path / "_tmp"

    bad = np.zeros((10, 10, 3), dtype=np.float32)

    with pytest.raises(TypeError):
        save_png_u8(target, bad, tmp_dir)


def test_save_png_u8_rejects_invalid_shape(tmp_path):
    target = tmp_path / "bad.png"
    tmp_dir = tmp_path / "_tmp"

    bad = np.zeros((10, 10, 2), dtype=np.uint8)

    with pytest.raises(ValueError):
        save_png_u8(target, bad, tmp_dir)