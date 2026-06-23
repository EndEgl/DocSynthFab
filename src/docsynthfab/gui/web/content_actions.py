# src/docsynthfab/gui/web/content_actions.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - nicegui>=2.0,<3.0

from __future__ import annotations

from typing import Any

from nicegui import ui

from docsynthfab.content import reset_content_to_samples, ensure_content_bank
from docsynthfab.gui.shared.paths import content_dir, normalize_config_path
from docsynthfab.gui.shared.upload_utils import read_upload_bytes

from .state import WebGuiState


def reset_content_csvs() -> None:
    try:
        target_dir = content_dir()
        reset_content_to_samples(target_dir)
        ui.notify(f"Content CSVs reset: {target_dir}", color="warning")
    except Exception as e:
        ui.notify(f"Content reset failed: {e}", color="negative")


def ensure_custom_content_csvs(state: WebGuiState) -> None:
    try:
        cfg = state.orchestrator.build_config_with_user_override(
            config_path=normalize_config_path(str(state.config_path_input.value or "")),
            overrides=None,
            raw_yaml_override_text=None,
        )

        ensure_content_bank(cfg)

        ui.notify(f"Custom content CSVs ready: {content_dir()}", color="positive")

    except Exception as e:
        ui.notify(f"Content setup failed: {e}", color="negative")


async def save_uploaded_content_csv(
    state: WebGuiState,
    e: Any,
    filename: str,
) -> None:
    try:
        target_dir = content_dir()
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / filename
        uploaded_bytes = await read_upload_bytes(e)

        text = uploaded_bytes.decode("utf-8-sig", errors="replace")
        target_path.write_text(text, encoding="utf-8-sig", newline="")

        cfg = state.orchestrator.build_config_with_user_override(
            config_path=normalize_config_path(str(state.config_path_input.value or "")),
            overrides=None,
            raw_yaml_override_text=None,
        )

        ensure_content_bank(cfg)

        ui.notify(f"{filename} saved to: {target_path}", color="positive")

    except Exception as ex:
        ui.notify(f"{filename} upload failed: {ex}", color="negative")



