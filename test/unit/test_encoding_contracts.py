from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".csv",
    ".toml",
    ".ini",
}

IGNORE_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "out",
    "outputs",
    "_tmp",
}

# Türkçe/UTF-8 bozulduğunda sık görülen mojibake kalıpları.
SUSPICIOUS_MOJIBAKE_PATTERNS = [
    "Ã¼",  # ü
    "Ãœ",  # Ü
    "Ã¶",  # ö
    "Ã–",  # Ö
    "Ã§",  # ç
    "Ã‡",  # Ç
    "Ä±",  # ı
    "Ä°",  # İ
    "ÄŸ",  # ğ
    "Äž",  # Ğ
    "ÅŸ",  # ş
    "Åž",  # Ş
    "â€™",
    "â€œ",
    "â€",
    "Â ",
    "\ufffd",  # replacement character
]


def _iter_text_files():
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue

        rel_parts = set(path.relative_to(PROJECT_ROOT).parts)

        if rel_parts & IGNORE_DIRS:
            continue

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        yield path


def test_project_text_files_are_readable_as_utf8():
    bad = []

    for path in _iter_text_files():
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            bad.append(
                {
                    "path": str(path.relative_to(PROJECT_ROOT)),
                    "error": str(exc),
                }
            )

    assert not bad, "Non UTF-8 text files found: " + repr(bad)


def test_project_text_files_do_not_contain_common_mojibake_patterns():
    bad = []

    for path in _iter_text_files():
        rel_path = path.relative_to(PROJECT_ROOT)

        # This file intentionally contains mojibake examples in
        # SUSPICIOUS_MOJIBAKE_PATTERNS, so it must not scan itself.
        if path.name == "test_encoding_contracts.py":
            continue

        text = path.read_text(encoding="utf-8", errors="replace")

        hits = [
            pattern
            for pattern in SUSPICIOUS_MOJIBAKE_PATTERNS
            if pattern in text
        ]

        if hits:
            bad.append(
                {
                    "path": str(rel_path),
                    "hits": hits,
                }
            )

    assert not bad, "Possible mojibake / broken UTF-8 detected: " + repr(bad)


    

def test_utf8_turkish_roundtrip_contract(tmp_path):
    sample = "İstanbul, ölçü, ğüşiöç, Türkçe karakter testi"

    path = tmp_path / "utf8_turkish.txt"
    path.write_text(sample, encoding="utf-8")

    loaded = path.read_text(encoding="utf-8")

    assert loaded == sample



