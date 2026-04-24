import numpy as np
import pytest
from PIL import Image

from ai1_gen.io.exporter import save_png_u8


def test_save_png_u8_writes_rgb_png(tmp_path):
    target = tmp_path / "images" / "page.png"
    tmp_dir = tmp_path / "_tmp"
    tmp_dir.mkdir()

    img = np.full((32, 64, 3), 255, dtype=np.uint8)
    save_png_u8(target, img, tmp_dir)

    assert target.exists()
    loaded = Image.open(target)
    assert loaded.size == (64, 32)


def test_save_png_u8_writes_grayscale_png(tmp_path):
    target = tmp_path / "masks" / "mask.png"
    tmp_dir = tmp_path / "_tmp"
    tmp_dir.mkdir()

    img = np.zeros((32, 64), dtype=np.uint8)
    img[0:5, 0:5] = 255
    save_png_u8(target, img, tmp_dir)

    assert target.exists()
    loaded = Image.open(target)
    assert loaded.size == (64, 32)


def test_save_png_u8_rejects_non_uint8_input(tmp_path):
    target = tmp_path / "bad.png"
    tmp_dir = tmp_path / "_tmp"
    tmp_dir.mkdir()

    bad = np.zeros((10, 10, 3), dtype=np.float32)

    with pytest.raises((TypeError, ValueError)):
        save_png_u8(target, bad, tmp_dir)


def test_save_png_u8_rejects_invalid_shape(tmp_path):
    target = tmp_path / "bad.png"
    tmp_dir = tmp_path / "_tmp"
    tmp_dir.mkdir()

    bad = np.zeros((10, 10, 2), dtype=np.uint8)

    with pytest.raises((TypeError, ValueError)):
        save_png_u8(target, bad, tmp_dir)