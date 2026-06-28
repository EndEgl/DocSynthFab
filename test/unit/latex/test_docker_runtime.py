from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from docsynthfab.latex import docker_runtime as dr


def test_project_root_from_this_file_points_to_project_root():
    root = dr._project_root_from_this_file()

    assert root.name.lower() == "docsynthfab"
    assert (root / "src").exists()
    assert (root / "src" / "docsynthfab").exists()


def test_run_docker_wraps_missing_docker_as_runtime_error(monkeypatch: pytest.MonkeyPatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("docker not found")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(dr.LatexDockerRuntimeError, match="docker/not-found"):
        dr._run_docker(["version"])


def test_run_docker_wraps_timeout_as_runtime_error(monkeypatch: pytest.MonkeyPatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="docker version", timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(dr.LatexDockerRuntimeError, match="docker/timeout"):
        dr._run_docker(["version"], timeout_s=1)


def test_run_docker_raises_when_check_true_and_returncode_nonzero(monkeypatch: pytest.MonkeyPatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["docker", "bad"],
            returncode=1,
            stdout="bad stdout",
            stderr="bad stderr",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(dr.LatexDockerRuntimeError, match="docker/command-failed"):
        dr._run_docker(["bad"], check=True)


def test_docker_available_true_when_version_command_succeeds(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        dr,
        "_run_docker",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["docker"],
            returncode=0,
            stdout="25.0.0\n",
            stderr="",
        ),
    )

    assert dr.docker_available() is True


def test_docker_available_false_when_command_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        dr,
        "_run_docker",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["docker"],
            returncode=1,
            stdout="",
            stderr="error",
        ),
    )

    assert dr.docker_available() is False


def test_image_exists_checks_docker_image_inspect(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(dr, "_run_docker", fake_run)

    assert dr.image_exists("latex-img:test") is True
    assert calls[0] == ["image", "inspect", "latex-img:test"]


def test_container_exists_detects_exact_name(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        dr,
        "_run_docker",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="docsynthfab_latex_renderer\n",
            stderr="",
        ),
    )

    assert dr.container_exists("docsynthfab_latex_renderer") is True


def test_container_running_detects_exact_name(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        dr,
        "_run_docker",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="docsynthfab_latex_renderer\n",
            stderr="",
        ),
    )

    assert dr.container_running("docsynthfab_latex_renderer") is True


def test_build_latex_image_fails_when_dockerfile_missing(tmp_path):
    docker_dir = tmp_path / "docker" / "latex"
    docker_dir.mkdir(parents=True)

    with pytest.raises(dr.LatexDockerRuntimeError, match="docker/latex-dockerfile-not-found"):
        dr.build_latex_image(docker_dir=docker_dir)


def test_build_latex_image_fails_when_server_missing(tmp_path):
    docker_dir = tmp_path / "docker" / "latex"
    docker_dir.mkdir(parents=True)
    (docker_dir / "Dockerfile").write_text("FROM python:3.11-slim", encoding="utf-8")

    with pytest.raises(dr.LatexDockerRuntimeError, match="docker/latex-server-not-found"):
        dr.build_latex_image(docker_dir=docker_dir)


def test_build_latex_image_fails_when_requirements_missing(tmp_path):
    docker_dir = tmp_path / "docker" / "latex"
    docker_dir.mkdir(parents=True)
    (docker_dir / "Dockerfile").write_text("FROM python:3.11-slim", encoding="utf-8")
    (docker_dir / "server.py").write_text("print('ok')", encoding="utf-8")

    with pytest.raises(dr.LatexDockerRuntimeError, match="docker/latex-requirements-not-found"):
        dr.build_latex_image(docker_dir=docker_dir)


def test_build_latex_image_runs_docker_build_when_files_exist(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    docker_dir = tmp_path / "docker" / "latex"
    docker_dir.mkdir(parents=True)
    (docker_dir / "Dockerfile").write_text("FROM python:3.11-slim", encoding="utf-8")
    (docker_dir / "server.py").write_text("print('ok')", encoding="utf-8")
    (docker_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(dr, "_run_docker", fake_run)

    dr.build_latex_image(image_name="test-img:latest", docker_dir=docker_dir)

    assert calls
    assert calls[0][0] == ["build", "-t", "test-img:latest", str(docker_dir)]
    assert calls[0][1]["check"] is True


def test_remove_latex_container_ignores_missing_container(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="missing")

    monkeypatch.setattr(dr, "_run_docker", fake_run)

    dr.remove_latex_container(container_name="missing")

    assert calls[0][0] == ["rm", "-f", "missing"]
    assert calls[0][1]["check"] is False


def test_start_latex_container_raises_when_docker_run_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        dr,
        "_run_docker",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="port already allocated",
        ),
    )

    with pytest.raises(dr.LatexDockerRuntimeError, match="docker/run-failed"):
        dr.start_latex_container(container_name="c", image_name="img")


def test_start_latex_container_uses_expected_docker_run_args(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc", stderr="")

    monkeypatch.setattr(dr, "_run_docker", fake_run)

    dr.start_latex_container(
        container_name="c",
        image_name="img:1",
        host_port=9090,
        container_port=8080,
    )

    assert calls[0][0] == [
        "run",
        "-d",
        "--name",
        "c",
        "-p",
        "9090:8080",
        "img:1",
    ]


def test_docker_logs_tail_combines_stdout_and_stderr(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        dr,
        "_run_docker",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="OUT",
            stderr="ERR",
        ),
    )

    logs = dr.docker_logs_tail(container_name="c", tail=10)

    assert "OUT" in logs
    assert "ERR" in logs


def test_health_ok_true_when_endpoint_returns_ok(monkeypatch: pytest.MonkeyPatch):
    class Resp:
        status_code = 200

        def json(self):
            return {"ok": True}

    class Requests:
        @staticmethod
        def get(url, timeout):
            return Resp()

    monkeypatch.setitem(__import__("sys").modules, "requests", Requests)

    assert dr._health_ok(http_base_url="http://x", timeout_s=1.0) is True


def test_health_ok_false_on_request_error(monkeypatch: pytest.MonkeyPatch):
    class Requests:
        @staticmethod
        def get(url, timeout):
            raise RuntimeError("down")

    monkeypatch.setitem(__import__("sys").modules, "requests", Requests)

    assert dr._health_ok(http_base_url="http://x", timeout_s=1.0) is False


def test_wait_for_latex_health_returns_true_when_health_becomes_ok(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = {"n": 0}

    def fake_health_ok(**kwargs):
        calls["n"] += 1
        return calls["n"] >= 2

    monkeypatch.setattr(dr, "_health_ok", fake_health_ok)
    monkeypatch.setattr(dr.time, "sleep", lambda *_args, **_kwargs: None)

    assert dr.wait_for_latex_health(timeout_s=1.0, poll_s=0.01) is True


def test_ensure_latex_container_returns_immediately_when_health_is_ok(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(dr, "_health_ok", lambda **kwargs: True)

    def should_not_call(*args, **kwargs):
        raise AssertionError("Docker should not be called when health is already OK")

    monkeypatch.setattr(dr, "docker_available", should_not_call)

    dr.ensure_latex_container(http_base_url="http://ok")


def test_ensure_latex_container_raises_when_docker_unavailable(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(dr, "_health_ok", lambda **kwargs: False)
    monkeypatch.setattr(dr, "docker_available", lambda: False)

    with pytest.raises(dr.LatexDockerRuntimeError, match="docker/not-available"):
        dr.ensure_latex_container(http_base_url="http://down")


def test_ensure_latex_container_raises_when_container_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(dr, "_health_ok", lambda **kwargs: False)
    monkeypatch.setattr(dr, "docker_available", lambda: True)
    monkeypatch.setattr(dr, "container_exists", lambda container_name: False)

    with pytest.raises(dr.LatexDockerRuntimeError, match="docker/latex-container-not-found"):
        dr.ensure_latex_container(container_name="c", image_name="img")


def test_ensure_latex_container_starts_existing_stopped_container(
    monkeypatch: pytest.MonkeyPatch,
):
    events = []

    monkeypatch.setattr(dr, "_health_ok", lambda **kwargs: False)
    monkeypatch.setattr(dr, "docker_available", lambda: True)
    monkeypatch.setattr(dr, "container_exists", lambda container_name: True)
    monkeypatch.setattr(dr, "container_running", lambda container_name: False)
    monkeypatch.setattr(
        dr,
        "start_existing_latex_container",
        lambda **kwargs: events.append(("start_existing", kwargs)),
    )
    monkeypatch.setattr(dr, "wait_for_latex_health", lambda **kwargs: True)

    dr.ensure_latex_container(container_name="c", image_name="img")

    assert events == [
        ("start_existing", {"container_name": "c", "timeout_s": 60})
    ]


def test_ensure_latex_container_raises_with_logs_when_started_container_stays_unhealthy(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(dr, "_health_ok", lambda **kwargs: False)
    monkeypatch.setattr(dr, "docker_available", lambda: True)
    monkeypatch.setattr(dr, "container_exists", lambda container_name: True)
    monkeypatch.setattr(dr, "container_running", lambda container_name: False)
    monkeypatch.setattr(dr, "start_existing_latex_container", lambda **kwargs: None)
    monkeypatch.setattr(dr, "wait_for_latex_health", lambda **kwargs: False)
    monkeypatch.setattr(dr, "docker_logs_tail", lambda **kwargs: "LOGTAIL")

    with pytest.raises(
        dr.LatexDockerRuntimeError,
        match="docker/latex-health-timeout-after-start",
    ) as exc:
        dr.ensure_latex_container(container_name="c", image_name="img")

    assert "LOGTAIL" in str(exc.value)


def test_ensure_latex_container_raises_when_running_container_is_unhealthy(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(dr, "_health_ok", lambda **kwargs: False)
    monkeypatch.setattr(dr, "docker_available", lambda: True)
    monkeypatch.setattr(dr, "container_exists", lambda container_name: True)
    monkeypatch.setattr(dr, "container_running", lambda container_name: True)
    monkeypatch.setattr(dr, "docker_logs_tail", lambda **kwargs: "RUNNING_LOGTAIL")

    with pytest.raises(
        dr.LatexDockerRuntimeError,
        match="docker/latex-container-running-but-unhealthy",
    ) as exc:
        dr.ensure_latex_container(container_name="c", image_name="img")

    assert "RUNNING_LOGTAIL" in str(exc.value)