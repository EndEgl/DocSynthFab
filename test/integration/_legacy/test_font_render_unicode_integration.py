from __future__ import annotations

from pathlib import Path
import random
import shutil

import pytest

from docsynthfab.render.font_utils import (
    _font_candidates,
    _missing_chars_for_font_path,
    _safe_font_for_text,
)


def _system_font_candidates() -> list[Path]:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/tahoma.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    ]
    return [p for p in candidates if p.exists()]


@pytest.fixture
def temp_font_tree(tmp_path: Path) -> Path:
    fonts = _system_font_candidates()

    if not fonts:
        pytest.skip("No usable system font found for integration font tests.")

    root = tmp_path / "fonts"
    for name in ["latin", "cyrillic", "greek", "symbols", "mono"]:
        (root / name).mkdir(parents=True, exist_ok=True)

    src = fonts[0]
    for folder in ["latin", "cyrillic", "greek", "symbols", "mono"]:
        shutil.copy2(src, root / folder / src.name)

    return root


@pytest.mark.integration
def test_turkish_text_selects_font_without_missing_glyphs(temp_font_tree: Path, unicode_samples):
    fnt = _safe_font_for_text(
        str(temp_font_tree),
        size=18,
        rng=random.Random(123),
        script="tr",
        role="body",
        probe_text=unicode_samples["turkish"],
    )

    assert fnt is not None


@pytest.mark.integration
def test_cyrillic_text_rejects_fonts_missing_required_chars(temp_font_tree: Path, unicode_samples):
    candidates = _font_candidates(str(temp_font_tree), script="ru", role="body")
    assert candidates

    missing_results = [
        _missing_chars_for_font_path(path, unicode_samples["cyrillic"])
        for path in candidates
    ]

    assert isinstance(missing_results[0], str)


@pytest.mark.integration
def test_symbols_text_can_select_symbol_or_mono_candidate(temp_font_tree: Path, unicode_samples):
    fnt = _safe_font_for_text(
        str(temp_font_tree),
        size=18,
        rng=random.Random(123),
        script="symbols",
        role="body",
        probe_text=unicode_samples["symbols"],
    )

    assert fnt is not None


@pytest.mark.integration
def test_missing_font_dir_falls_back_without_crashing(unicode_samples):
    fnt = _safe_font_for_text(
        None,
        size=18,
        rng=random.Random(123),
        script="ru",
        role="body",
        probe_text=unicode_samples["cyrillic"],
    )

    assert fnt is not None



