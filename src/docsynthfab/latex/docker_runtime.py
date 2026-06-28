# src/docsynthfab/latex/docker_runtime.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - requests>=2.31,<3.0

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from .errors import LatexDockerRuntimeError


DEFAULT_CONTAINER_NAME = "docsynthfab_latex_renderer"
DEFAULT_IMAGE_NAME = "ai1-gen-latex-renderer:latest"

# Current runtime decision:
# - Do not change/remove the existing container.
# - The existing container publishes host 8080 to container 8080.
DEFAULT_HOST_PORT = 8080
DEFAULT_CONTAINER_PORT = 8080
DEFAULT_HTTP_BASE_URL = "http://127.0.0.1:8080"


def _project_root_from_this_file() -> Path:
    """
    Resolve the project root from this module path.

    Expected file location:
    - <project_root>/src/docsynthfab/latex/docker_runtime.py
    """
    return Path(__file__).resolve().parents[3]


def _run_docker(
    args: list[str],
    *,
    timeout_s: int = 60,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """
    Run a Docker CLI command and return the completed process.

    The function never relies on shell=True. This keeps command execution safer
    and avoids quoting issues on Windows.
    """
    cmd = ["docker", *args]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError as exc:
        raise LatexDockerRuntimeError(
            "docker/not-found: Docker CLI was not found. "
            "Docker Desktop or Docker Engine must be installed and available on PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise LatexDockerRuntimeError(
            f"docker/timeout: {' '.join(cmd)} timed out after {timeout_s} seconds."
        ) from exc

    if check and proc.returncode != 0:
        raise LatexDockerRuntimeError(
            "docker/command-failed\n"
            f"cmd: {' '.join(cmd)}\n"
            f"returncode: {proc.returncode}\n"
            f"stdout:\n{(proc.stdout or '')[-3000:]}\n"
            f"stderr:\n{(proc.stderr or '')[-5000:]}"
        )

    return proc


def docker_available() -> bool:
    """Return True when Docker CLI can reach the Docker daemon."""
    try:
        proc = _run_docker(
            ["version", "--format", "{{.Server.Version}}"],
            timeout_s=20,
            check=False,
        )
        return proc.returncode == 0
    except Exception:
        return False


def image_exists(image_name: str = DEFAULT_IMAGE_NAME) -> bool:
    """Return True when the requested Docker image exists locally."""
    proc = _run_docker(
        ["image", "inspect", image_name],
        timeout_s=30,
        check=False,
    )
    return proc.returncode == 0


def container_exists(container_name: str = DEFAULT_CONTAINER_NAME) -> bool:
    """Return True when a container with the exact configured name exists."""
    proc = _run_docker(
        [
            "ps",
            "-a",
            "--filter",
            f"name=^{container_name}$",
            "--format",
            "{{.Names}}",
        ],
        timeout_s=30,
        check=False,
    )
    return container_name in (proc.stdout or "").splitlines()


def container_running(container_name: str = DEFAULT_CONTAINER_NAME) -> bool:
    """Return True when a container with the exact configured name is running."""
    proc = _run_docker(
        [
            "ps",
            "--filter",
            f"name=^{container_name}$",
            "--format",
            "{{.Names}}",
        ],
        timeout_s=30,
        check=False,
    )
    return container_name in (proc.stdout or "").splitlines()

def start_existing_latex_container(
    *,
    container_name: str = DEFAULT_CONTAINER_NAME,
    timeout_s: int = 60,
) -> None:
    """
    Start an existing LaTeX renderer container.

    Important:
    - This does NOT create a new container.
    - This does NOT remove/recreate the container.
    - It only runs: docker start <container_name>
    """
    proc = _run_docker(
        ["start", container_name],
        timeout_s=timeout_s,
        check=False,
    )

    if proc.returncode != 0:
        raise LatexDockerRuntimeError(
            "docker/start-existing-container-failed\n"
            f"cmd: docker start {container_name}\n"
            f"stdout:\n{(proc.stdout or '')[-3000:]}\n"
            f"stderr:\n{(proc.stderr or '')[-5000:]}"
        )


def build_latex_image(
    *,
    image_name: str = DEFAULT_IMAGE_NAME,
    docker_dir: Optional[Path] = None,
    timeout_s: int = 1800,
) -> None:
    """
    Build the LaTeX HTTP renderer Docker image.

    Expected build context:
    - docker/latex/Dockerfile
    - docker/latex/server.py
    - docker/latex/requirements.txt
    """
    build_dir = Path(docker_dir) if docker_dir is not None else (
        _project_root_from_this_file() / "docker" / "latex"
    )

    dockerfile = build_dir / "Dockerfile"
    server_py = build_dir / "server.py"
    requirements = build_dir / "requirements.txt"

    if not dockerfile.exists():
        raise LatexDockerRuntimeError(
            f"docker/latex-dockerfile-not-found: {dockerfile}"
        )

    if not server_py.exists():
        raise LatexDockerRuntimeError(
            f"docker/latex-server-not-found: {server_py}"
        )

    if not requirements.exists():
        raise LatexDockerRuntimeError(
            f"docker/latex-requirements-not-found: {requirements}"
        )

    _run_docker(
        ["build", "-t", image_name, str(build_dir)],
        timeout_s=timeout_s,
        check=True,
    )


def remove_latex_container(
    *,
    container_name: str = DEFAULT_CONTAINER_NAME,
    timeout_s: int = 60,
) -> None:
    """
    Remove only the configured LaTeX renderer container.

    Missing containers are not treated as errors.

    Note:
    - ensure_latex_container() no longer calls this by default.
    - Keep this function only for explicit/manual maintenance.
    """
    _run_docker(
        ["rm", "-f", container_name],
        timeout_s=timeout_s,
        check=False,
    )


def start_latex_container(
    *,
    container_name: str = DEFAULT_CONTAINER_NAME,
    image_name: str = DEFAULT_IMAGE_NAME,
    host_port: int = DEFAULT_HOST_PORT,
    container_port: int = DEFAULT_CONTAINER_PORT,
    timeout_s: int = 120,
) -> None:
    """Start the LaTeX renderer container in detached mode."""
    proc = _run_docker(
        [
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{host_port}:{container_port}",
            image_name,
        ],
        timeout_s=timeout_s,
        check=False,
    )

    if proc.returncode != 0:
        raise LatexDockerRuntimeError(
            "docker/run-failed\n"
            f"cmd: docker run -d --name {container_name} "
            f"-p {host_port}:{container_port} {image_name}\n"
            f"stdout:\n{(proc.stdout or '')[-3000:]}\n"
            f"stderr:\n{(proc.stderr or '')[-5000:]}"
        )


def docker_logs_tail(
    *,
    container_name: str = DEFAULT_CONTAINER_NAME,
    tail: int = 120,
) -> str:
    """Return the tail of Docker logs for diagnostics."""
    proc = _run_docker(
        ["logs", "--tail", str(tail), container_name],
        timeout_s=30,
        check=False,
    )

    return (proc.stdout or "")[-5000:] + "\n" + (proc.stderr or "")[-5000:]


def _health_ok(
    *,
    http_base_url: str = DEFAULT_HTTP_BASE_URL,
    timeout_s: float = 2.0,
) -> bool:
    """Return True when the renderer health endpoint reports ok=true."""
    try:
        import requests

        response = requests.get(
            f"{http_base_url.rstrip('/')}/health",
            timeout=timeout_s,
        )

        return response.status_code == 200 and bool(response.json().get("ok", False))

    except Exception:
        return False


def wait_for_latex_health(
    *,
    http_base_url: str = DEFAULT_HTTP_BASE_URL,
    timeout_s: float = 45.0,
    poll_s: float = 0.75,
) -> bool:
    """Poll the renderer health endpoint until it becomes ready or times out."""
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        if _health_ok(http_base_url=http_base_url, timeout_s=2.5):
            return True

        time.sleep(poll_s)

    return False


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)

    if value is None:
        return default

    return str(value).strip().lower() not in {"0", "false", "no", "off", ""}


def _resolve_runtime_config(
    *,
    http_base_url: str,
    container_name: Optional[str],
    image_name: Optional[str],
    host_port: Optional[int],
    container_port: Optional[int],
) -> tuple[str, str, str, int, int]:
    resolved_container_name = container_name or os.environ.get(
        "AI1_LATEX_CONTAINER_NAME",
        DEFAULT_CONTAINER_NAME,
    )
    resolved_image_name = image_name or os.environ.get(
        "AI1_LATEX_IMAGE",
        DEFAULT_IMAGE_NAME,
    )
    resolved_host_port = int(
        host_port or os.environ.get("AI1_LATEX_HOST_PORT", DEFAULT_HOST_PORT)
    )
    resolved_container_port = int(
        container_port or os.environ.get(
            "AI1_LATEX_CONTAINER_PORT",
            DEFAULT_CONTAINER_PORT,
        )
    )
    resolved_http_base_url = os.environ.get(
        "AI1_LATEX_HTTP_BASE_URL",
        http_base_url,
    )

    return (
        resolved_http_base_url,
        resolved_container_name,
        resolved_image_name,
        resolved_host_port,
        resolved_container_port,
    )

def ensure_latex_container(
    *,
    http_base_url: str = DEFAULT_HTTP_BASE_URL,
    container_name: Optional[str] = None,
    image_name: Optional[str] = None,
    docker_dir: Optional[Path] = None,
    host_port: Optional[int] = None,
    container_port: Optional[int] = None,
    build_if_missing: bool = False,
    force_recreate_if_unhealthy: bool = False,
    create_if_missing: bool = False,
) -> None:
    """
    Ensure that the existing Docker-based LaTeX HTTP renderer is available.

    Current safety policy:
    - If /health already returns ok=true, do nothing.
    - If the configured container exists but is stopped, run docker start.
    - If the configured container exists and is running but unhealthy, raise.
    - If the configured container does not exist, raise.
    - Do NOT remove containers.
    - Do NOT create containers.
    - Do NOT rebuild images.

    This is intentional because the LaTeX renderer container should be managed
    as a stable external runtime dependency.
    """
    (
        resolved_http_base_url,
        resolved_container_name,
        resolved_image_name,
        resolved_host_port,
        resolved_container_port,
    ) = _resolve_runtime_config(
        http_base_url=http_base_url,
        container_name=container_name,
        image_name=image_name,
        host_port=host_port,
        container_port=container_port,
    )

    # Already healthy.
    if _health_ok(http_base_url=resolved_http_base_url, timeout_s=2.0):
        return

    if not docker_available():
        raise LatexDockerRuntimeError(
            "docker/not-available: Docker is not running or the Docker CLI is not reachable."
        )

    # Strict mode: container must already exist.
    if not container_exists(resolved_container_name):
        raise LatexDockerRuntimeError(
            "docker/latex-container-not-found\n"
            f"container_name: {resolved_container_name}\n"
            f"http_base_url: {resolved_http_base_url}\n"
            "The LaTeX renderer container does not exist. "
            "This code is configured to never create containers automatically."
        )

    # If container exists but is stopped, start it.
    if not container_running(resolved_container_name):
        start_existing_latex_container(
            container_name=resolved_container_name,
            timeout_s=60,
        )

        if wait_for_latex_health(
            http_base_url=resolved_http_base_url,
            timeout_s=60.0,
        ):
            return

        logs = docker_logs_tail(container_name=resolved_container_name)

        raise LatexDockerRuntimeError(
            "docker/latex-health-timeout-after-start\n"
            f"Container was started but /health did not become ready: "
            f"{resolved_http_base_url.rstrip('/')}/health\n"
            f"container_name: {resolved_container_name}\n"
            f"image_name: {resolved_image_name}\n"
            f"host_port: {resolved_host_port}\n"
            f"container_port: {resolved_container_port}\n"
            f"docker logs tail:\n{logs}"
        )

    # Container is running, but health failed.
    logs = docker_logs_tail(container_name=resolved_container_name)

    raise LatexDockerRuntimeError(
        "docker/latex-container-running-but-unhealthy\n"
        f"container_name: {resolved_container_name}\n"
        f"http_base_url: {resolved_http_base_url}\n"
        "The container exists and is running, but /health is not OK. "
        "It was not removed, recreated, rebuilt, or modified.\n"
        f"docker logs tail:\n{logs}"
    )



