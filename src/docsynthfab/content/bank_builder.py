# src/docsynthfab/content/bank_builder.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
#
# Content bank builder.
# Reads the legacy data/content/words.csv + data/content/sentences.csv files and,
# when configured, every CSV under data/content/word_banks/*.csv.
# The word-bank directory is the preferred public/open-source path for
# multilingual OCR/Document AI content.

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _as_enabled(v: Any) -> bool:
    if v is None:
        return True
    s = str(v).strip().lower()
    return s not in {"0", "false", "no", "off", ""}


def _as_weight(v: Any) -> float:
    if v is None or str(v).strip() == "":
        return 1.0
    try:
        return max(0.0, float(v))
    except Exception:
        return 1.0


def _load_words_csv(path: Path, *, source_name: str | None = None) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = str(row.get("word", "")).strip()
            if not word:
                continue
            if not _as_enabled(row.get("enabled")):
                continue

            item = {
                "text": word,
                "lang": str(row.get("lang", "unknown")).strip() or "unknown",
                "script": str(row.get("script", "unknown")).strip() or "unknown",
                "alphabet_profile": str(row.get("alphabet_profile", "unknown")).strip() or "unknown",
                "weight": _as_weight(row.get("weight")),
                "category": str(row.get("category", "general")).strip() or "general",
            }

            if source_name:
                item["source"] = source_name

            out.append(item)

    return out


def _load_word_banks_dir(path: Path | None) -> List[Dict[str, Any]]:
    if path is None or not path.exists() or not path.is_dir():
        return []

    out: List[Dict[str, Any]] = []
    for csv_path in sorted(path.glob("*.csv")):
        out.extend(_load_words_csv(csv_path, source_name=f"word_banks/{csv_path.name}"))

    return out


def _load_sentences_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = str(row.get("text", "")).strip()
            if not text:
                continue
            if not _as_enabled(row.get("enabled")):
                continue

            out.append(
                {
                    "text": text,
                    "lang": str(row.get("lang", "unknown")).strip() or "unknown",
                    "script": str(row.get("script", "unknown")).strip() or "unknown",
                    "alphabet_profile": str(row.get("alphabet_profile", "unknown")).strip() or "unknown",
                    "weight": _as_weight(row.get("weight")),
                    "category": str(row.get("category", "general")).strip() or "general",
                }
            )

    return out


def _dedupe_items(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    out: List[Dict[str, Any]] = []

    for item in items:
        key = (
            str(item.get("text", "")).strip(),
            str(item.get("lang", "")).strip().lower(),
            str(item.get("script", "")).strip().lower(),
            str(item.get("alphabet_profile", "")).strip().lower(),
        )

        if not key[0] or key in seen:
            continue

        seen.add(key)
        out.append(item)

    return out


def _collect_label_registry(
    words: List[Dict[str, Any]],
    sentences: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    seen: set[tuple[str, str]] = set()

    def _add(kind: str, value: Any) -> None:
        v = str(value or "").strip()
        if not v:
            return
        seen.add((kind, v))

    for item in words:
        _add("lang", item.get("lang"))
        _add("script", item.get("script"))
        _add("alphabet_profile", item.get("alphabet_profile"))
        _add("source", item.get("source"))

    for item in sentences:
        _add("lang", item.get("lang"))
        _add("script", item.get("script"))
        _add("alphabet_profile", item.get("alphabet_profile"))

    return [{"kind": kind, "value": value} for kind, value in sorted(seen, key=lambda x: (x[0], x[1]))]


def _write_label_registry_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["kind", "value"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_content_bank_json(
    *,
    words_csv_path: str | Path,
    sentences_csv_path: str | Path,
    out_json_path: str | Path,
    label_registry_csv_path: str | Path | None = None,
    word_banks_dir: str | Path | None = None,
) -> Dict[str, Any]:
    words_path = Path(words_csv_path)
    sentences_path = Path(sentences_csv_path)
    out_path = Path(out_json_path)
    bank_dir_path = Path(word_banks_dir) if word_banks_dir is not None else None

    legacy_words = _load_words_csv(words_path, source_name=words_path.name if words_path.exists() else None)
    bank_words = _load_word_banks_dir(bank_dir_path)
    words = _dedupe_items([*legacy_words, *bank_words])
    sentences = _load_sentences_csv(sentences_path)

    obj = {
        "version": "content-bank-v1",
        "words": words,
        "sentences": sentences,
        "meta": {
            "legacy_words_count": len(legacy_words),
            "word_bank_words_count": len(bank_words),
            "words_count": len(words),
            "sentences_count": len(sentences),
            "word_banks_dir": str(bank_dir_path) if bank_dir_path is not None else "",
        },
    }

    if label_registry_csv_path is not None:
        registry_rows = _collect_label_registry(words, sentences)
        _write_label_registry_csv(Path(label_registry_csv_path), registry_rows)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return obj




