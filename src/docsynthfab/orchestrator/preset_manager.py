# src/docsynthfab/orchestrator/preset_manager.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - PyYAML>=6.0,<7.0

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from .models import RunRequest


class PresetManager:
    def __init__(self, presets_dir: str | Path = "presets") -> None:
        self.presets_dir = Path(presets_dir)
        self.presets_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in name).strip("._")
        if not safe:
            raise ValueError("preset/invalid-name")
        return self.presets_dir / f"{safe}.yaml"

    def save_preset(self, name: str, request: RunRequest) -> Path:
        path = self._path(name)
        obj = request.to_dict()
        obj["preset_name"] = name
        path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return path

    def load_preset(self, name: str) -> RunRequest:
        path = self._path(name)
        if not path.exists():
            raise FileNotFoundError(str(path))
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError("preset/invalid-yaml")
        return RunRequest(
            config_path=str(raw.get("config_path", "")),
            out_root=str(raw.get("out_root", "")),
            pages=int(raw.get("pages", 0)),
            workers=int(raw.get("workers", 0)),
            seed=int(raw.get("seed", -1)),
            preset_name=str(raw.get("preset_name", name)),
            smoke_test=bool(raw.get("smoke_test", False)),
            overrides=dict(raw.get("overrides", {}) or {}),
            notes=str(raw.get("notes", "")),
        )

    def list_presets(self) -> List[str]:
        return sorted(p.stem for p in self.presets_dir.glob("*.yaml"))

    def delete_preset(self, name: str) -> bool:
        path = self._path(name)
        if not path.exists():
            return False
        path.unlink()
        return True



