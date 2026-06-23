from __future__ import annotations

import random
from pathlib import Path

from docsynthfab.render.font_coverage import check_font_coverage, check_font_text
from docsynthfab.render.font_size import font_size_config, sample_font_size_px
from docsynthfab.render.font_utils import (
    _font_candidates,
    _font_dirs_for_script_and_role,
    _normalize_script_name,
    _safe_font_for_text,
    _sample_probe_text_for_script,
)


class Cfg:
    def __init__(self, raw):
        self.raw = raw


def test_font_size_config_reads_nested_render_text_font_size():
    cfg = Cfg(
        {
            "render": {
                "text": {
                    "font_size": {
                        "min_px": 11,
                        "max_px": 19,
                    }
                }
            }
        }
    )

    out = font_size_config(cfg)

    assert out["min_px"] == 11
    assert out["max_px"] == 19


def test_sample_font_size_uniform_stays_inside_bounds():
    cfg = {
        "render": {
            "text": {
                "font_size": {
                    "distribution": "uniform",
                    "min_px": 8,
                    "max_px": 12,
                }
            }
        }
    }

    for seed in range(20):
        value = sample_font_size_px(random.Random(seed), cfg)
        assert 8 <= value <= 12


def test_sample_font_size_swaps_reversed_bounds():
    cfg = {
        "render": {
            "text": {
                "font_size": {
                    "distribution": "uniform",
                    "min_px": 18,
                    "max_px": 10,
                }
            }
        }
    }

    value = sample_font_size_px(random.Random(123), cfg)

    assert 10 <= value <= 18


def test_sample_font_size_gaussian_stays_inside_bounds():
    cfg = {
        "render": {
            "text": {
                "font_size": {
                    "distribution": "gaussian",
                    "min_px": 9,
                    "max_px": 17,
                    "mean_ratio": 0.5,
                    "std_ratio": 0.2,
                }
            }
        }
    }

    for seed in range(20):
        value = sample_font_size_px(random.Random(seed), cfg)
        assert 9 <= value <= 17


def test_normalize_script_name_aliases():
    assert _normalize_script_name("en") == "latin"
    assert _normalize_script_name("cyrillic") == "ru"
    assert _normalize_script_name("greek") == "el"
    assert _normalize_script_name("han") == "zh"
    assert _normalize_script_name("") == "latin"


def test_sample_probe_text_for_script_and_role():
    assert "Başlık" in _sample_probe_text_for_script("tr", "title")
    assert "data" in _sample_probe_text_for_script("latin", "table")
    assert "√" in _sample_probe_text_for_script("symbols", "body")


def test_font_dirs_for_script_and_role_uses_existing_dirs(tmp_path: Path):
    (tmp_path / "latin").mkdir()
    (tmp_path / "mono").mkdir()

    dirs = _font_dirs_for_script_and_role(str(tmp_path), "latin", "table")

    assert tmp_path / "latin" in dirs
    assert tmp_path / "mono" in dirs


def test_font_candidates_collects_font_extensions_without_loading(tmp_path: Path):
    latin = tmp_path / "latin"
    mono = tmp_path / "mono"
    latin.mkdir()
    mono.mkdir()

    (latin / "A.ttf").write_bytes(b"dummy")
    (mono / "B.otf").write_bytes(b"dummy")
    (mono / "C.ttc").write_bytes(b"dummy")

    candidates = _font_candidates(str(tmp_path), "latin", "body")

    assert {p.name for p in candidates} >= {"A.ttf", "B.otf", "C.ttc"}


def test_safe_font_for_text_falls_back_to_pil_default_when_no_font_dir():
    font = _safe_font_for_text(
        None,
        size=12,
        rng=random.Random(123),
        script="latin",
        role="body",
        probe_text="example data line",
    )

    assert getattr(font, "_docsynthfab_font_path", "") == "__PIL_DEFAULT__"
    assert getattr(font, "_docsynthfab_font_index", None) == -1


def test_check_font_text_reports_empty_and_missing_font():
    empty = check_font_text(font_path="missing.ttf", text="")
    missing = check_font_text(font_path="missing.ttf", text="hello")

    assert empty.ok is False
    assert empty.reason == "empty-text"
    assert missing.ok is False
    assert missing.reason.startswith("font-load-failed:")


def test_check_font_coverage_respects_limit():
    report = check_font_coverage(
        font_path="missing.ttf",
        texts=["a", "b", "c"],
        limit=2,
    )

    assert report.total == 2
    assert report.ok == 0
    assert report.failed == 2
    assert len(report.items) == 2
    assert report.to_dict()["total"] == 2