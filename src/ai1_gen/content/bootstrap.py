# src/ai1_gen/content/bootstrap.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class ContentPaths:
    words_csv: Path
    sentences_csv: Path
    generated_json: Path
    label_registry_csv: Path

    def as_resolved_dict(self) -> Dict[str, str]:
        return {
            "words_csv": str(self.words_csv.resolve()),
            "sentences_csv": str(self.sentences_csv.resolve()),
            "generated_json": str(self.generated_json.resolve()),
            "label_registry_csv": str(self.label_registry_csv.resolve()),
        }


def _content_cfg(cfg: Any) -> Dict[str, Any]:
    if not hasattr(cfg, "raw"):
        return {}
    return cfg.raw.get("content", {}) or {}


def _resolve_content_paths(cfg: Any) -> ContentPaths:
    source_cfg = (_content_cfg(cfg).get("source", {}) or {})

    return ContentPaths(
        words_csv=Path(str(source_cfg.get("words_csv", "data/content/words.csv"))),
        sentences_csv=Path(str(source_cfg.get("sentences_csv", "data/content/sentences.csv"))),
        generated_json=Path(str(source_cfg.get("generated_json", "data/content/content_bank.json"))),
        label_registry_csv=Path(str(source_cfg.get("label_registry_csv", "data/content/label_registry.csv"))),
    )


def _write_text_file(path: Path, content: str, *, force: bool = False) -> None:
    if path.exists() and not force:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    encoding = "utf-8-sig" if path.suffix.lower() == ".csv" else "utf-8"
    path.write_text(content, encoding=encoding, newline="")


def _write_sample_sources_if_missing(paths: ContentPaths) -> None:
    _write_text_file(paths.words_csv, _WORDS_SAMPLE)
    _write_text_file(paths.sentences_csv, _SENTENCES_SAMPLE)
    _write_text_file(paths.label_registry_csv, _LABEL_REGISTRY_SAMPLE)


def _write_sample_sources_force(paths: ContentPaths) -> None:
    _write_text_file(paths.words_csv, _WORDS_SAMPLE, force=True)
    _write_text_file(paths.sentences_csv, _SENTENCES_SAMPLE, force=True)
    _write_text_file(paths.label_registry_csv, _LABEL_REGISTRY_SAMPLE, force=True)

    
def _build_generated_json(paths: ContentPaths) -> None:
    paths.generated_json.parent.mkdir(parents=True, exist_ok=True)

    build_content_bank_json(
        words_csv_path=paths.words_csv,
        sentences_csv_path=paths.sentences_csv,
        out_json_path=paths.generated_json,
        label_registry_csv_path=paths.label_registry_csv,
    )


def ensure_content_bank(cfg: Any) -> Dict[str, str]:
    content_cfg = _content_cfg(cfg)
    paths = _resolve_content_paths(cfg)

    _write_sample_sources_if_missing(paths)

    generate_if_missing = bool(content_cfg.get("generate_json_if_missing", True))
    regenerate_on_start = bool(content_cfg.get("regenerate_json_on_start", False))

    should_generate = regenerate_on_start or (
        generate_if_missing and not paths.generated_json.exists()
    )

    if should_generate:
        _build_generated_json(paths)

    return paths.as_resolved_dict()


def reset_generated_content_files(cfg: Any) -> Dict[str, str]:
    paths = _resolve_content_paths(cfg)

    _write_sample_sources_if_missing(paths)

    if paths.generated_json.exists():
        paths.generated_json.unlink()

    if paths.label_registry_csv.exists():
        paths.label_registry_csv.unlink()

    _build_generated_json(paths)

    return paths.as_resolved_dict()


def reset_content_to_samples(cfg: Any) -> Dict[str, str]:
    paths = _resolve_content_paths(cfg)

    paths.generated_json.parent.mkdir(parents=True, exist_ok=True)

    _write_sample_sources_force(paths)
    _build_generated_json(paths)

    return paths.as_resolved_dict()