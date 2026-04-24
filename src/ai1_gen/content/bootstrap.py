# src/ai1_gen/content/bootstrap.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .bank_builder import build_content_bank_json


_WORDS_SAMPLE = """word,lang,script,alphabet_profile,weight,category,enabled
invoice,en,latin,latin_basic,1.0,business,1
contract,en,latin,latin_basic,1.0,business,1
analysis,en,latin,latin_basic,1.0,general,1
veri,tr,latin,latin_tr,1.0,general,1
rapor,tr,latin,latin_tr,1.0,general,1
"""

_SENTENCES_SAMPLE = """text,lang,script,alphabet_profile,weight,category,enabled
This is a sample sentence.,en,latin,latin_basic,1.0,general,1
The quarterly report was approved.,en,latin,latin_basic,1.0,business,1
Bu bir örnek cümledir.,tr,latin,latin_tr,1.0,general,1
Tablo verileri yeniden gözden geçirildi.,tr,latin,latin_tr,1.0,business,1
"""

_LABEL_REGISTRY_SAMPLE = """kind,value
lang,en
lang,tr
script,latin
alphabet_profile,latin_basic
alphabet_profile,latin_tr
"""


def _write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")


def ensure_content_bank(cfg: Any) -> Dict[str, str]:
    content_cfg = (cfg.raw.get("content", {}) or {}) if hasattr(cfg, "raw") else {}
    source_cfg = content_cfg.get("source", {}) or {}

    words_csv = Path(str(source_cfg.get("words_csv", "data/content/words.csv")))
    sentences_csv = Path(str(source_cfg.get("sentences_csv", "data/content/sentences.csv")))
    generated_json = Path(str(source_cfg.get("generated_json", "data/content/content_bank.json")))
    label_registry_csv = Path(str(source_cfg.get("label_registry_csv", "data/content/label_registry.csv")))

    _write_if_missing(words_csv, _WORDS_SAMPLE)
    _write_if_missing(sentences_csv, _SENTENCES_SAMPLE)
    _write_if_missing(label_registry_csv, _LABEL_REGISTRY_SAMPLE)

    generate_if_missing = bool(content_cfg.get("generate_json_if_missing", True))
    regenerate_on_start = bool(content_cfg.get("regenerate_json_on_start", False))

    if regenerate_on_start or (generate_if_missing and not generated_json.exists()):
        generated_json.parent.mkdir(parents=True, exist_ok=True)
        build_content_bank_json(
            words_csv_path=words_csv,
            sentences_csv_path=sentences_csv,
            out_json_path=generated_json,
            label_registry_csv_path=label_registry_csv,
        )

    return {
        "words_csv": str(words_csv.resolve()),
        "sentences_csv": str(sentences_csv.resolve()),
        "generated_json": str(generated_json.resolve()),
        "label_registry_csv": str(label_registry_csv.resolve()),
    }


def reset_generated_content_files(cfg: Any) -> Dict[str, str]:
    info = ensure_content_bank(cfg)

    words_csv = Path(info["words_csv"])
    sentences_csv = Path(info["sentences_csv"])
    generated_json = Path(info["generated_json"])
    label_registry_csv = Path(info["label_registry_csv"])

    if generated_json.exists():
        generated_json.unlink()

    if label_registry_csv.exists():
        label_registry_csv.unlink()

    build_content_bank_json(
        words_csv_path=words_csv,
        sentences_csv_path=sentences_csv,
        out_json_path=generated_json,
        label_registry_csv_path=label_registry_csv,
    )

    return {
        "words_csv": str(words_csv.resolve()),
        "sentences_csv": str(sentences_csv.resolve()),
        "generated_json": str(generated_json.resolve()),
        "label_registry_csv": str(label_registry_csv.resolve()),
    }


def reset_content_to_samples(cfg: Any) -> Dict[str, str]:
    content_cfg = (cfg.raw.get("content", {}) or {}) if hasattr(cfg, "raw") else {}
    source_cfg = content_cfg.get("source", {}) or {}

    words_csv = Path(str(source_cfg.get("words_csv", "data/content/words.csv")))
    sentences_csv = Path(str(source_cfg.get("sentences_csv", "data/content/sentences.csv")))
    generated_json = Path(str(source_cfg.get("generated_json", "data/content/content_bank.json")))
    label_registry_csv = Path(str(source_cfg.get("label_registry_csv", "data/content/label_registry.csv")))

    words_csv.parent.mkdir(parents=True, exist_ok=True)
    sentences_csv.parent.mkdir(parents=True, exist_ok=True)
    generated_json.parent.mkdir(parents=True, exist_ok=True)
    label_registry_csv.parent.mkdir(parents=True, exist_ok=True)

    words_csv.write_text(_WORDS_SAMPLE, encoding="utf-8", newline="")
    sentences_csv.write_text(_SENTENCES_SAMPLE, encoding="utf-8", newline="")
    label_registry_csv.write_text(_LABEL_REGISTRY_SAMPLE, encoding="utf-8", newline="")

    build_content_bank_json(
        words_csv_path=words_csv,
        sentences_csv_path=sentences_csv,
        out_json_path=generated_json,
        label_registry_csv_path=label_registry_csv,
    )

    return {
        "words_csv": str(words_csv.resolve()),
        "sentences_csv": str(sentences_csv.resolve()),
        "generated_json": str(generated_json.resolve()),
        "label_registry_csv": str(label_registry_csv.resolve()),
    }