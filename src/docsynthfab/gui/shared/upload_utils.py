# src/docsynthfab/gui/shared/upload_utils.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# Shared upload helpers for NiceGUI and future GUI layers.

from __future__ import annotations

import asyncio
from typing import Any


async def read_upload_bytes(e: Any) -> bytes:
    """
    Read an upload payload safely.

    Supports NiceGUI upload events where e.content.read() may return either
    bytes directly or a coroutine.
    """
    src = getattr(e, "content", None) or getattr(e, "file", None)

    if src is None:
        raise RuntimeError("Upload payload not found")

    if hasattr(src, "read"):
        data = src.read()

        if asyncio.iscoroutine(data):
            data = await data

    else:
        data = src

    if isinstance(data, bytes):
        return data

    if isinstance(data, bytearray):
        return bytes(data)

    if isinstance(data, str):
        return data.encode("utf-8")

    raise RuntimeError(f"Unsupported upload payload type: {type(data).__name__}")



