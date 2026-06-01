# src/ai1_gen/gui/shared/paths.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# Shared path helpers for desktop and web GUI layers.
# This module uses only the Python standard library.

from __future__ import annotations

import os
import subprocess
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PACKAGE_ROOT.parent
PROJECT_ROOT = SRC_ROOT.parent

DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "default.yaml"

WEB_GUI_OUT_DIR = PROJECT_ROOT / "out" / "web_gui"
ACTIVE_RUN_STATE_PATH = WEB_GUI_OUT_DIR / "_active_run_state.json"
GUI_EVENT_LOG_PATH = WEB_GUI_OUT_DIR / "_gui_live_events.log"


def resolve_user_path(
    value: str,
    *,
    base_dir: Path = PROJECT_ROOT,
    allow_empty: bool = False,
) -> str:
    """
    Resolve a user-provided path safely.

    Relative paths are resolved against the project root by default.
    """
    txt = str(value or "").strip()

    if not txt:
        return "" if allow_empty else str(base_dir.resolve())

    p = Path(txt)

    if not p.is_absolute():
        p = (base_dir / p).resolve()
    else:
        p = p.resolve()

    return str(p)


def normalize_config_path(value: str) -> str:
    """Normalize the config path used by GUI runs."""
    return resolve_user_path(value, base_dir=PROJECT_ROOT, allow_empty=False)


def normalize_out_root(value: str) -> str:
    """Normalize the output root path used by GUI runs."""
    return resolve_user_path(value, base_dir=PROJECT_ROOT, allow_empty=True)


def content_dir() -> Path:
    """Return the default content CSV directory."""
    return PROJECT_ROOT / "data" / "content"


def open_path(path: str) -> None:
    """
    Open a file or folder with the operating system's default handler.

    This is shared by desktop and web GUI actions.
    """
    p = str(Path(path))

    if os.name == "nt":
        os.startfile(p)  # type: ignore[attr-defined]
        return

    if os.uname().sysname == "Darwin":
        subprocess.Popen(["open", p])
        return

    subprocess.Popen(["xdg-open", p])