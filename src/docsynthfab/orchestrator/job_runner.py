# src/docsynthfab/orchestrator/job_runner.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .models import RunRequest


class JobRunner:
    def start_subprocess_run(
        self,
        request: RunRequest,
        *,
        effective_config_path: str,
        stdout_log_path: str,
        stderr_log_path: str,
    ) -> subprocess.Popen:
        this_file = Path(__file__).resolve()
        src_root = this_file.parents[2]      # .../src
        project_root = this_file.parents[3]  # .../docsynthfab project root

        cmd = [
            sys.executable,
            "-m",
            "docsynthfab.cli",
            "--config",
            str(Path(effective_config_path).resolve()),
        ]

        if request.out_root:
            cmd.extend(["--out", str(request.out_root)])
        if request.pages > 0:
            cmd.extend(["--pages", str(request.pages)])
        if request.workers > 0:
            cmd.extend(["--workers", str(request.workers)])
        if request.seed >= 0:
            cmd.extend(["--seed", str(request.seed)])

        Path(stdout_log_path).parent.mkdir(parents=True, exist_ok=True)
        Path(stderr_log_path).parent.mkdir(parents=True, exist_ok=True)

        stdout_f = open(stdout_log_path, "w", encoding="utf-8")
        stderr_f = open(stderr_log_path, "w", encoding="utf-8")

        env = os.environ.copy()
        old_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            str(src_root)
            if not old_pythonpath
            else str(src_root) + os.pathsep + old_pythonpath
        )

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=stdout_f,
                stderr=stderr_f,
                text=True,
                cwd=str(project_root),
                env=env,
            )
        except Exception:
            stdout_f.close()
            stderr_f.close()
            raise

        return proc



