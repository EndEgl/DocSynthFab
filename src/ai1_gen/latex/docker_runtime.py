# src/ai1_gen/latex/docker_runtime.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - requests>=2.31,<3.0
#
# External runtime:
# - Docker CLI PATH içinde olmalı.
# - Docker Desktop / Docker Engine çalışıyor olmalı.
#
# Varsayılan image:
# - latex-gen-server:0.1
#
# Beklenen Docker build context:
# - <project_root>/docker/latex/Dockerfile
# - <project_root>/docker/latex/server.py
# - <project_root>/docker/latex/requirements.txt

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional


class LatexDockerRuntimeError(RuntimeError):
    pass


DEFAULT_CONTAINER_NAME = "ai1_gen_latex_renderer"
DEFAULT_IMAGE_NAME = "latex-gen-server:0.1"
DEFAULT_HOST_PORT = 8080
DEFAULT_CONTAINER_PORT = 8080
DEFAULT_HTTP_BASE_URL = "http://127.0.0.1:8080"


def _project_root_from_this_file() -> Path:
    # .../src/ai1_gen/latex/docker_runtime.py
    # parents[3] -> project root: ai1_gen
    return Path(__file__).resolve().parents[3]


def _run_docker(
    args: list[str],
    *,
    timeout_s: int = 60,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            ["docker", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError as e:
        raise LatexDockerRuntimeError(
            "docker/not-found: Docker CLI bulunamadı. Docker Desktop kurulu ve PATH içinde olmalı."
        ) from e
    except subprocess.TimeoutExpired as e:
        raise LatexDockerRuntimeError(
            f"docker/timeout: docker {' '.join(args)} zaman aşımına uğradı."
        ) from e

    if check and proc.returncode != 0:
        raise LatexDockerRuntimeError(
            "docker/command-failed\n"
            f"cmd: docker {' '.join(args)}\n"
            f"returncode: {proc.returncode}\n"
            f"stdout:\n{proc.stdout[-3000:]}\n"
            f"stderr:\n{proc.stderr[-5000:]}"
        )

    return proc


def docker_available() -> bool:
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
    proc = _run_docker(
        ["image", "inspect", image_name],
        timeout_s=30,
        check=False,
    )
    return proc.returncode == 0


def container_exists(container_name: str = DEFAULT_CONTAINER_NAME) -> bool:
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
    return container_name in proc.stdout.splitlines()


def container_running(container_name: str = DEFAULT_CONTAINER_NAME) -> bool:
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
    return container_name in proc.stdout.splitlines()


def build_latex_image(
    *,
    image_name: str = DEFAULT_IMAGE_NAME,
    docker_dir: Optional[Path] = None,
    timeout_s: int = 1800,
) -> None:
    if docker_dir is None:
        docker_dir = _project_root_from_this_file() / "docker" / "latex"

    dockerfile = docker_dir / "Dockerfile"
    server_py = docker_dir / "server.py"
    requirements = docker_dir / "requirements.txt"

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
        [
            "build",
            "-t",
            image_name,
            str(docker_dir),
        ],
        timeout_s=timeout_s,
        check=True,
    )


def remove_latex_container(
    *,
    container_name: str = DEFAULT_CONTAINER_NAME,
    timeout_s: int = 60,
) -> None:
    # Container yoksa hata sayma.
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
            f"cmd: docker run -d --name {container_name} -p {host_port}:{container_port} {image_name}\n"
            f"stdout:\n{proc.stdout[-3000:]}\n"
            f"stderr:\n{proc.stderr[-5000:]}"
        )


def docker_logs_tail(
    *,
    container_name: str = DEFAULT_CONTAINER_NAME,
    tail: int = 120,
) -> str:
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
    try:
        import requests

        resp = requests.get(
            f"{http_base_url.rstrip('/')}/health",
            timeout=timeout_s,
        )
        return resp.status_code == 200 and bool(resp.json().get("ok", False))
    except Exception:
        return False


def wait_for_latex_health(
    *,
    http_base_url: str = DEFAULT_HTTP_BASE_URL,
    timeout_s: float = 45.0,
    poll_s: float = 0.75,
) -> bool:
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        if _health_ok(http_base_url=http_base_url, timeout_s=2.5):
            return True
        time.sleep(poll_s)

    return False


def ensure_latex_container(
    *,
    http_base_url: str = DEFAULT_HTTP_BASE_URL,
    container_name: Optional[str] = None,
    image_name: Optional[str] = None,
    docker_dir: Optional[Path] = None,
    host_port: Optional[int] = None,
    container_port: Optional[int] = None,
    build_if_missing: bool = True,
    force_recreate_if_unhealthy: bool = True,
) -> None:
    """
    LaTeX HTTP renderer container'ını garantiye alır.

    Davranış:
    1. /health çalışıyorsa hiçbir şey yapmaz.
    2. Docker çalışıyor mu kontrol eder.
    3. Image yoksa docker/latex içinden build eder.
    4. Health yoksa ve aynı container adı varsa kaldırır.
    5. Container'ı başlatır.
    6. /health gelene kadar bekler.

    Güvenlik:
    - Sadece container_name ile eşleşen container'ı kaldırır.
    - Başka container'ları temizlemez.
    """

    container_name = container_name or os.environ.get(
        "AI1_LATEX_CONTAINER_NAME",
        DEFAULT_CONTAINER_NAME,
    )
    image_name = image_name or os.environ.get(
        "AI1_LATEX_IMAGE",
        DEFAULT_IMAGE_NAME,
    )
    host_port = int(host_port or os.environ.get("AI1_LATEX_HOST_PORT", DEFAULT_HOST_PORT))
    container_port = int(
        container_port or os.environ.get("AI1_LATEX_CONTAINER_PORT", DEFAULT_CONTAINER_PORT)
    )

    # URL dışarıdan env ile verilirse onu kullan.
    http_base_url = os.environ.get("AI1_LATEX_HTTP_BASE_URL", http_base_url)

    if _health_ok(http_base_url=http_base_url, timeout_s=2.0):
        return

    if not docker_available():
        raise LatexDockerRuntimeError(
            "docker/not-available: Docker çalışmıyor veya Docker CLI erişilemiyor."
        )

    if not image_exists(image_name):
        if not build_if_missing:
            raise LatexDockerRuntimeError(
                f"docker/image-not-found: {image_name}"
            )
        build_latex_image(
            image_name=image_name,
            docker_dir=docker_dir,
        )

    # Health yoksa container var ama bozuk/durmuş/portsuz olabilir.
    # Sadece kendi container adımızı temizliyoruz.
    if force_recreate_if_unhealthy and container_exists(container_name):
        remove_latex_container(container_name=container_name)

    # Eğer container yoksa başlat.
    if not container_running(container_name):
        start_latex_container(
            container_name=container_name,
            image_name=image_name,
            host_port=host_port,
            container_port=container_port,
        )

    if not wait_for_latex_health(
        http_base_url=http_base_url,
        timeout_s=60.0,
    ):
        logs = docker_logs_tail(container_name=container_name)
        raise LatexDockerRuntimeError(
            "docker/latex-health-timeout\n"
            f"Container started but /health did not become ready: {http_base_url.rstrip('/')}/health\n"
            f"container_name: {container_name}\n"
            f"image_name: {image_name}\n"
            f"host_port: {host_port}\n"
            f"container_port: {container_port}\n"
            f"docker logs tail:\n{logs}"
        )