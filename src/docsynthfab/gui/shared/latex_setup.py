# src/docsynthfab/gui/shared/latex_setup.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - requests>=2.31,<3.0

from __future__ import annotations

import socket
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_LATEX_HTTP_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_LATEX_PORT = 8080


@dataclass(frozen=True)
class LatexSetupStatus:
    docker_cli_available: bool
    docker_daemon_available: bool
    port_open: bool
    health_ok: bool
    http_base_url: str
    port: int
    docker_error: str
    health_error: str

    @property
    def ok(self) -> bool:
        return bool(
            self.docker_cli_available
            and self.docker_daemon_available
            and self.port_open
            and self.health_ok
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["ok"] = self.ok
        return data


def project_root_from_file() -> Path:
    """
    Resolve the project root from this file.

    Current file:
      src/docsynthfab/gui/shared/latex_setup.py

    Project root:
      docsynthfab/
    """
    return Path(__file__).resolve().parents[4]


def default_latex_docker_dir() -> Path:
    return project_root_from_file() / "docker" / "latex-renderer"


def _parse_port_from_url(http_base_url: str) -> int:
    text = str(http_base_url or DEFAULT_LATEX_HTTP_BASE_URL).strip()

    if ":" not in text:
        return DEFAULT_LATEX_PORT

    try:
        tail = text.rsplit(":", 1)[-1]
        tail = tail.split("/", 1)[0]
        return int(tail)
    except Exception:
        return DEFAULT_LATEX_PORT


def _check_port_open(host: str = "127.0.0.1", port: int = DEFAULT_LATEX_PORT) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=1.0):
            return True
    except Exception:
        return False


def _run_command(args: list[str], timeout_s: float = 4.0) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )

        output = "\n".join(
            part.strip()
            for part in (result.stdout, result.stderr)
            if part and part.strip()
        )

        return result.returncode == 0, output

    except FileNotFoundError as e:
        return False, str(e)

    except subprocess.TimeoutExpired:
        return False, f"Command timed out: {' '.join(args)}"

    except Exception as e:
        return False, repr(e)


def check_docker_status() -> tuple[bool, bool, str]:
    """
    Return:
      docker_cli_available, docker_daemon_available, error_text
    """
    cli_ok, cli_out = _run_command(["docker", "--version"], timeout_s=3.0)

    if not cli_ok:
        return False, False, cli_out or "Docker CLI is not available."

    daemon_ok, daemon_out = _run_command(["docker", "info"], timeout_s=5.0)

    if not daemon_ok:
        return True, False, daemon_out or "Docker daemon is not running."

    return True, True, ""


def check_latex_health(http_base_url: str = DEFAULT_LATEX_HTTP_BASE_URL) -> tuple[bool, str]:
    """
    Check the LaTeX renderer health endpoint.

    Expected endpoint:
      http://127.0.0.1:8080/health

    Uses stdlib urllib to avoid making the GUI depend on requests.
    """
    from urllib.error import URLError
    from urllib.request import urlopen

    base = str(http_base_url or DEFAULT_LATEX_HTTP_BASE_URL).rstrip("/")
    url = f"{base}/health"

    try:
        with urlopen(url, timeout=2.0) as response:
            code = int(getattr(response, "status", 200))
            body = response.read(2048).decode("utf-8", errors="replace")

        if 200 <= code < 300:
            return True, body.strip()

        return False, f"Health endpoint returned HTTP {code}: {body[:300]}"

    except URLError as e:
        return False, str(e)

    except Exception as e:
        return False, repr(e)


def inspect_latex_setup(
    http_base_url: str = DEFAULT_LATEX_HTTP_BASE_URL,
) -> LatexSetupStatus:
    base_url = str(http_base_url or DEFAULT_LATEX_HTTP_BASE_URL).strip()
    port = _parse_port_from_url(base_url)

    docker_cli_ok, docker_daemon_ok, docker_error = check_docker_status()
    port_open = _check_port_open(port=port)
    health_ok, health_error = check_latex_health(base_url)

    return LatexSetupStatus(
        docker_cli_available=bool(docker_cli_ok),
        docker_daemon_available=bool(docker_daemon_ok),
        port_open=bool(port_open),
        health_ok=bool(health_ok),
        http_base_url=base_url,
        port=int(port),
        docker_error=str(docker_error or ""),
        health_error="" if health_ok else str(health_error or ""),
    )


def normalize_latex_mix(
    text_value: Any,
    table_value: Any,
    latex_value: Any,
) -> Dict[str, float]:
    """
    Normalize Text/Table/LaTeX values for the dedicated LaTeX page.

    Unlike the main generator, this function allows LaTeX > 0.
    """
    def read_percent(value: Any, default: float) -> float:
        try:
            return max(0.0, min(100.0, float(value)))
        except Exception:
            return float(default)

    text = read_percent(text_value, 40.0)
    table = read_percent(table_value, 20.0)
    latex = read_percent(latex_value, 40.0)

    total = text + table + latex

    if total <= 0:
        text, table, latex = 40.0, 20.0, 40.0
        total = 100.0

    return {
        "text": round((text / total) * 100.0, 4),
        "table": round((table / total) * 100.0, 4),
        "latex": round((latex / total) * 100.0, 4),
    }


def latex_mix_label(mix: Dict[str, float]) -> str:
    return (
        f"Text {float(mix.get('text', 0.0)):.0f}% / "
        f"Table {float(mix.get('table', 0.0)):.0f}% / "
        f"LaTeX {float(mix.get('latex', 0.0)):.0f}%"
    )


def latex_run_overrides(
    *,
    text_value: Any,
    table_value: Any,
    latex_value: Any,
    http_base_url: str = DEFAULT_LATEX_HTTP_BASE_URL,
    missing_behavior: str = "fallback",
) -> Dict[str, Any]:
    """
    Build overrides for a dedicated LaTeX-focused generation run.

    This should be used only from the LaTeX page, not the main generator.
    """
    mix = normalize_latex_mix(text_value, table_value, latex_value)

    return {
        "content.block_mix": mix,
        "render.latex.enable": True,
        "render.latex.backend": "http",
        "render.latex.http_base_url": str(http_base_url or DEFAULT_LATEX_HTTP_BASE_URL).rstrip("/"),
        "render.latex.missing_behavior": str(missing_behavior or "fallback"),
    }


def format_latex_status_text(status: LatexSetupStatus) -> str:
    lines: list[str] = []

    lines.append(f"Renderer URL: {status.http_base_url}")
    lines.append(f"Port: {status.port}")
    lines.append("")

    lines.append(
        "Docker CLI: "
        + ("OK" if status.docker_cli_available else "MISSING")
    )
    lines.append(
        "Docker daemon: "
        + ("OK" if status.docker_daemon_available else "NOT RUNNING")
    )
    lines.append(
        "Port open: "
        + ("OK" if status.port_open else "CLOSED")
    )
    lines.append(
        "Health check: "
        + ("OK" if status.health_ok else "FAILED")
    )
    lines.append("")

    if status.docker_error:
        lines.append("Docker message:")
        lines.append(status.docker_error[:1000])
        lines.append("")

    if status.health_error:
        lines.append("Health message:")
        lines.append(status.health_error[:1000])
        lines.append("")

    lines.append("Overall: " + ("OK" if status.ok else "needs attention"))

    return "\n".join(lines)


def docker_command_text(
    *,
    image_name: str = "docsynthfab-latex-renderer",
    container_name: str = "docsynthfab_latex_renderer",
    port: int = DEFAULT_LATEX_PORT,
) -> str:
    docker_dir = default_latex_docker_dir()

    return "\n".join(
        [
            "# 1) Install Docker Desktop first if Docker is missing.",
            "# 2) Build the LaTeX renderer image from the project root:",
            f'cd "{project_root_from_file()}"',
            f'docker build -t {image_name} "{docker_dir}"',
            "",
            "# 3) Run the renderer:",
            (
                f"docker run --rm -p {port}:8080 "
                f"--name {container_name} {image_name}"
            ),
            "",
            "# 4) Health check:",
            f"curl http://127.0.0.1:{port}/health",
        ]
    )


def short_latex_help_text() -> str:
    return (
        "LaTeX generation is intentionally separated from the main generator. "
        "Use this page only when you want equation/math-heavy synthetic pages. "
        "The main generator remains Text/Table-only by default."
    )


def latex_renderer_url_text(http_base_url: Optional[str] = None) -> str:
    return str(http_base_url or DEFAULT_LATEX_HTTP_BASE_URL).rstrip("/")



