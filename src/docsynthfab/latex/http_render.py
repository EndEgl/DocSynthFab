# src/docsynthfab/latex/http_render.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12
# - requests>=2.31,<3.0

from __future__ import annotations

import base64
import contextlib
import hashlib
import os
import tempfile
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Dict

from PIL import Image
import requests

from .docker_runtime import ensure_latex_container
from .errors import LatexDockerRuntimeError, LatexRenderError
from .image_cleanup import crop_rgba_to_alpha_bbox
from .normalize import normalize_latex_expr


if os.name == "nt":
    import msvcrt
else:
    import fcntl


# Current runtime decision:
# - Existing Docker container name: docsynthfab_latex_renderer
# - Existing image name: ai1-gen-latex-renderer:latest
# - Existing host mapping: 8080 -> 8080
# - Therefore the default renderer URL is http://127.0.0.1:8080
#
# Override when needed:
#   PowerShell:
#     $env:AI1_LATEX_HTTP_BASE_URL="http://127.0.0.1:8080"
DEFAULT_HTTP_BASE_URL = os.environ.get(
    "AI1_LATEX_HTTP_BASE_URL",
    "http://127.0.0.1:8080",
)


_RENDERER_READY_CACHE: dict[str, bool] = {}


def auto_docker_enabled() -> bool:
    """
    Return whether the renderer should auto-start Docker when needed.

    Set this to 0 if you want to manage the container manually:

        PowerShell:
            $env:AI1_LATEX_AUTO_DOCKER="0"

    Default is enabled, but docker_runtime.py is configured not to remove,
    recreate, build, or replace the existing renderer container.
    """
    return str(os.environ.get("AI1_LATEX_AUTO_DOCKER", "1")).strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def latex_client_lock_enabled() -> bool:
    """
    Return whether Python workers should serialize access to the HTTP renderer.

    This should stay enabled for a single Docker LaTeX renderer.

    Disable only if you later implement a true renderer pool, for example:
    - renderer_1: http://127.0.0.1:8081
    - renderer_2: http://127.0.0.1:8082
    - renderer_3: http://127.0.0.1:8083
    """
    return str(os.environ.get("AI1_LATEX_CLIENT_LOCK", "1")).strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _latex_lock_name_for_base_url(base_url: str) -> str:
    """
    Create a stable lock filename per renderer URL.

    This means different renderer URLs can have independent locks.
    """
    digest = hashlib.sha1(
        base_url.encode("utf-8", errors="ignore"),
    ).hexdigest()[:16]

    return f"docsynthfab_latex_renderer_{digest}.lock"


@contextlib.contextmanager
def latex_render_process_lock(
    *,
    http_base_url: str,
    timeout_s: float,
    poll_s: float = 0.10,
):
    """
    Cross-process lock for the Docker LaTeX renderer.

    Why this exists:
    - DocSynthFab can run multiple page workers.
    - Multiple workers may need LaTeX at the same time.
    - A single Docker renderer should not receive uncontrolled parallel /render requests.
    - Server-side RENDER_LOCK is still useful, but client-side locking prevents
      request pile-up and client timeouts while waiting inside the server.

    This lock works across Python processes on Windows and Linux.
    """
    if not latex_client_lock_enabled():
        yield
        return

    base = str(http_base_url or DEFAULT_HTTP_BASE_URL).rstrip("/")
    lock_name = _latex_lock_name_for_base_url(base)

    lock_dir = Path(tempfile.gettempdir()) / "docsynthfab_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / lock_name

    deadline = time.time() + max(1.0, float(timeout_s))

    with lock_path.open("a+b") as fh:
        acquired = False

        while not acquired:
            try:
                if os.name == "nt":
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                acquired = True

            except OSError:
                if time.time() >= deadline:
                    raise LatexRenderError(
                        "render/latex-client-lock-timeout: "
                        f"Could not acquire LaTeX renderer client lock. "
                        f"base_url={base!r}, timeout_s={timeout_s}"
                    )

                time.sleep(float(poll_s))

        try:
            yield

        finally:
            try:
                if os.name == "nt":
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def check_latex_http_health(
    http_base_url: str = DEFAULT_HTTP_BASE_URL,
    *,
    timeout_s: int | float = 2,
) -> None:
    """
    Verify that http_base_url is really the LaTeX renderer.

    Important:
    - A plain HTTP 200 HTML page is not enough.
    - The endpoint must look like the LaTeX renderer.
    - Health check must fail fast and never hang.
    """
    base = str(http_base_url or DEFAULT_HTTP_BASE_URL).rstrip("/")

    candidates = [
        f"{base}/health",
        f"{base}/healthz",
    ]

    last_error = ""

    for url in candidates:
        try:
            resp = requests.get(url, timeout=float(timeout_s))

        except requests.Timeout as exc:
            last_error = f"timeout calling {url}: {exc!r}"
            continue

        except Exception as exc:
            last_error = f"failed calling {url}: {exc!r}"
            continue

        status_code = int(getattr(resp, "status_code", 0) or 0)
        text = str(getattr(resp, "text", "") or "")

        if status_code >= 400:
            last_error = (
                f"{url} returned status={status_code} "
                f"body={text[:200]!r}"
            )
            continue

        try:
            data = resp.json()
        except Exception:
            data = None

        if isinstance(data, dict):
            keys = " ".join(str(k).lower() for k in data.keys())
            values = " ".join(str(v).lower() for v in data.values())

            # Accept common renderer health formats:
            # {"ok": true}
            # {"status": "ok"}
            # {"service": "latex-renderer"}
            if (
                "latex" in keys
                or "latex" in values
                or "renderer" in keys
                or "renderer" in values
                or data.get("ok") is True
                or str(data.get("status", "")).lower() in {"ok", "ready", "healthy"}
            ):
                return

        lowered = text.lower()

        if (
            "latex" in lowered
            and (
                "renderer" in lowered
                or "ok" in lowered
                or "ready" in lowered
                or "healthy" in lowered
            )
        ):
            return

        last_error = (
            f"{url} responded but does not look like the LaTeX renderer. "
            f"status={status_code} body={text[:200]!r}"
        )

    raise LatexRenderError(
        f"render/latex-http-health-failed: base_url={base!r}; {last_error}"
    )


def ensure_http_renderer_ready(
    http_base_url: str = DEFAULT_HTTP_BASE_URL,
) -> None:
    """
    Ensure the Docker HTTP renderer is running when auto-Docker is enabled.

    Current behavior:
    - If AI1_LATEX_AUTO_DOCKER=0, do nothing here.
    - If auto-Docker is enabled, only use the existing configured container.
    - If the existing container is stopped, docker_runtime starts it with docker start.
    - Do not remove, recreate, build, or replace the container.
    """
    if not auto_docker_enabled():
        return

    try:
        ensure_latex_container(
            http_base_url=http_base_url,
            container_name=os.environ.get(
                "AI1_LATEX_CONTAINER_NAME",
                "docsynthfab_latex_renderer",
            ),
            image_name=os.environ.get(
                "AI1_LATEX_IMAGE",
                "ai1-gen-latex-renderer:latest",
            ),
            host_port=int(os.environ.get("AI1_LATEX_HOST_PORT", "8080")),
            container_port=int(os.environ.get("AI1_LATEX_CONTAINER_PORT", "8080")),
            build_if_missing=False,
            force_recreate_if_unhealthy=False,
            create_if_missing=False,
        )

    except LatexDockerRuntimeError as exc:
        raise LatexRenderError(
            f"render/latex-docker-runtime-failed: {exc}"
        ) from exc


def ensure_http_renderer_ready_once(http_base_url: str) -> None:
    """
    Prepare/check the renderer once per Python process and base URL.

    This avoids running /health before every single LaTeX expression.
    """
    base = str(http_base_url or DEFAULT_HTTP_BASE_URL).rstrip("/")

    if _RENDERER_READY_CACHE.get(base):
        return

    ensure_http_renderer_ready(http_base_url=base)
    check_latex_http_health(http_base_url=base, timeout_s=2)

    _RENDERER_READY_CACHE[base] = True


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except Exception:
        return float(default)


def render_latex_to_rgba_http(
    latex_expr: str,
    *,
    http_base_url: str = DEFAULT_HTTP_BASE_URL,
    timeout_s: int = 12,
    raster_dpi: int = 300,
) -> Image.Image:
    """
    Render a LaTeX expression through the HTTP renderer.

    Expected endpoints:
    - GET  /health or /healthz
    - POST /render

    Important:
    - Health is checked once per renderer base URL, not before every formula.
    - HTTP 200 does not always mean render success.
      The renderer can return {"ok": false, "error": "..."} with status 200.
    - Client-side process locking prevents multiple AI1 worker processes from
      overwhelming one Docker LaTeX renderer.
    - This function raises LatexRenderError with explicit error context.
    """
    base = str(http_base_url or DEFAULT_HTTP_BASE_URL).rstrip("/")
    url = f"{base}/render"

    normalized_expr = normalize_latex_expr(latex_expr)

    # Prepare/check renderer once per process.
    ensure_http_renderer_ready_once(http_base_url=base)

    safe_timeout_s = max(3, min(int(timeout_s), 120))
    safe_dpi = max(72, min(int(raster_dpi), 900))

    payload: Dict[str, Any] = {
        "expr": normalized_expr,
        "dpi": safe_dpi,
        "timeout_s": safe_timeout_s,
    }

    # This is the queue wait timeout. It must be long enough for workers=6+
    # and many LaTeX pages. This is not the pdflatex timeout; it is the time
    # a worker may wait before it gets the right to call POST /render.
    client_lock_timeout_s = _env_float(
        "AI1_LATEX_CLIENT_LOCK_TIMEOUT_S",
        900.0,
    )

    # This is the actual HTTP request timeout after the lock is acquired.
    # Since the server no longer receives uncontrolled parallel requests,
    # this can stay bounded but should still be larger than pdflatex timeout.
    http_timeout_s = _env_float(
        "AI1_LATEX_HTTP_REQUEST_TIMEOUT_S",
        float(safe_timeout_s) + 30.0,
    )

    try:
        with latex_render_process_lock(
            http_base_url=base,
            timeout_s=client_lock_timeout_s,
        ):
            response = requests.post(
                url,
                json=payload,
                timeout=http_timeout_s,
            )

    except requests.Timeout as exc:
        raise LatexRenderError(
            "render/latex-http-timeout: "
            f"HTTP renderer timed out. url={url}, "
            f"latex_timeout_s={safe_timeout_s}, "
            f"http_timeout_s={http_timeout_s}"
        ) from exc

    except requests.RequestException as exc:
        raise LatexRenderError(
            "render/latex-http-unreachable: "
            f"HTTP renderer is not reachable. url={url}, error={exc}"
        ) from exc

    try:
        response.raise_for_status()

    except requests.HTTPError as exc:
        raise LatexRenderError(
            "render/latex-http-status-error: "
            f"status={response.status_code}, url={url}, body={response.text[-1200:]}"
        ) from exc

    try:
        data = response.json()

    except Exception as exc:
        raise LatexRenderError(
            "render/latex-http-invalid-json: "
            f"renderer did not return valid JSON. status={response.status_code}, "
            f"body={response.text[-1200:]}"
        ) from exc

    if not isinstance(data, dict):
        raise LatexRenderError(
            "render/latex-http-invalid-response: "
            f"renderer JSON is not an object. type={type(data).__name__}"
        )

    # HTTP 200 can still mean LaTeX render failed.
    if not bool(data.get("ok", False)):
        error = str(data.get("error", "unknown"))
        stdout = str(data.get("stdout", "") or "")
        stderr = str(data.get("stderr", "") or "")

        raise LatexRenderError(
            "render/latex-http-failed: "
            f"error={error}\n"
            f"expr={normalized_expr[:300]!r}\n"
            f"stdout={stdout[-1200:]}\n"
            f"stderr={stderr[-1200:]}"
        )

    png_b64 = data.get("png_base64")

    if not isinstance(png_b64, str) or not png_b64.strip():
        raise LatexRenderError(
            "render/latex-http-empty-response: missing png_base64"
        )

    try:
        png_bytes = base64.b64decode(png_b64)
        image = Image.open(BytesIO(png_bytes)).convert("RGBA")

    except Exception as exc:
        raise LatexRenderError(
            "render/latex-http-decode-failed: could not decode png_base64"
        ) from exc

    return crop_rgba_to_alpha_bbox(image, pad=4)



