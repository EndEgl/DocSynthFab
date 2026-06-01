# test/e2e/e2e_support.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - Pillow>=10,<12

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ai1_gen.orchestrator import RunOrchestrator, RunRequest


TERMINAL_STATES = {"done", "completed", "failed", "error", "cancelled"}


def fresh_output_dir(path: Path) -> Path:
    """
    Remove and recreate one E2E output directory.

    This is important because E2E outputs are persistent under D:\\ai1_test_2_100.
    Without cleanup, old generated files can corrupt count-based assertions.
    """
    if path.exists():
        shutil.rmtree(path)

    path.mkdir(parents=True, exist_ok=True)
    return path


def project_root_from_test_file(file_path: str | Path) -> Path:
    return Path(file_path).resolve().parents[2]


def default_config_path(project_root: Path) -> Path:
    path = project_root / "configs" / "default.yaml"
    assert path.exists(), f"default config not found: {path}"
    return path


def wait_for_run(
    orch: RunOrchestrator,
    run_id: str,
    *,
    timeout_s: float = 180.0,
):
    deadline = time.time() + timeout_s
    last_status = None

    while time.time() < deadline:
        last_status = orch.get_status(run_id)
        state = str(getattr(last_status, "state", ""))

        if state in TERMINAL_STATES:
            return last_status

        time.sleep(0.25)

    raise TimeoutError(f"Run did not finish in {timeout_s}s. Last status={last_status!r}")


def run_backend_generation(
    *,
    config_path: Path,
    out_root: Path,
    pages: int = 3,
    workers: int = 1,
    seed: int = 123,
    overrides: dict[str, Any] | None = None,
    raw_yaml_override_text: str | None = None,
    timeout_s: float = 180.0,
) -> tuple[RunOrchestrator, str, Any]:
    orch = RunOrchestrator()

    req = RunRequest(
        config_path=str(config_path),
        out_root=str(out_root),
        pages=pages,
        workers=workers,
        seed=seed,
        smoke_test=False,
        overrides=overrides or {},
        raw_yaml_override_text=raw_yaml_override_text,
    )

    run_id = orch.start(req)
    status = wait_for_run(orch, run_id, timeout_s=timeout_s)

    return orch, run_id, status


def run_cli_generation(
    *,
    project_root: Path,
    config_path: Path,
    out_root: Path,
    pages: int = 3,
    workers: int = 1,
    seed: int = 123,
    export: str = "native,segformer,coco",
    timeout_s: float = 240.0,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()

    src_root = project_root / "src"
    old_pythonpath = env.get("PYTHONPATH", "")

    if old_pythonpath:
        env["PYTHONPATH"] = str(src_root) + os.pathsep + old_pythonpath
    else:
        env["PYTHONPATH"] = str(src_root)

    cmd = [
        sys.executable,
        "-m",
        "ai1_gen.cli",
        "--config",
        str(config_path),
        "--out",
        str(out_root),
        "--pages",
        str(int(pages)),
        "--workers",
        str(int(workers)),
        "--seed",
        str(int(seed)),
        "--export",
        export,
    ]

    return subprocess.run(
        cmd,
        cwd=str(project_root),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout_s,
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def try_load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.json") if p.is_file())


def png_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.png") if p.is_file())


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def required_output_dirs() -> list[str]:
    return [
        "images",
        "masks",
        "ann",
        "gt",
        "splits",
        "reports",
        "exports",
    ]


def required_report_files() -> list[str]:
    """
    Required report files for the first E2E acceptance layer.

    features.jsonl is intentionally not required here because the current
    report writer contract is already covered by features.csv. If jsonl export
    becomes a stable report contract later, add a dedicated test for it.
    """
    return [
        "run_manifest.json",
        "dataset_card.md",
        "label_schema.json",
        "label_schema.md",
        "features.csv",
        "diversity_summary.json",
        "diversity_summary.csv",
        "diversity_report.md",
    ]


def assert_run_completed(status: Any) -> None:
    state = str(getattr(status, "state", ""))
    assert state in {"done", "completed"}, f"run did not complete cleanly: {status!r}"


def assert_output_package_exists(out_root: Path) -> None:
    for dirname in required_output_dirs():
        assert (out_root / dirname).exists(), f"missing output dir: {dirname}"

    for filename in required_report_files():
        assert (out_root / "reports" / filename).exists(), f"missing report file: {filename}"


def assert_page_counts_match(out_root: Path, expected_pages: int | None = None) -> dict[str, int]:
    images = sorted((out_root / "images").glob("*.png"))
    anns = sorted((out_root / "ann").glob("*.json"))
    gts = sorted((out_root / "gt").glob("*.json"))

    assert images, "no images generated"
    assert anns, "no annotations generated"
    assert gts, "no ground truth files generated"

    assert len(images) == len(anns) == len(gts), {
        "images": len(images),
        "ann": len(anns),
        "gt": len(gts),
    }

    if expected_pages is not None:
        assert len(images) == expected_pages, {
            "expected": expected_pages,
            "images": len(images),
            "ann": len(anns),
            "gt": len(gts),
        }

    return {
        "image_count": len(images),
        "ann_count": len(anns),
        "gt_count": len(gts),
    }


def load_ann_gt_pairs(out_root: Path) -> list[tuple[Path, dict[str, Any], Path, dict[str, Any]]]:
    ann_paths = sorted((out_root / "ann").glob("*.json"))
    gt_paths = sorted((out_root / "gt").glob("*.json"))

    gt_by_stem = {p.stem: p for p in gt_paths}

    pairs: list[tuple[Path, dict[str, Any], Path, dict[str, Any]]] = []

    for ann_path in ann_paths:
        gt_path = gt_by_stem.get(ann_path.stem)
        assert gt_path is not None, f"missing GT for annotation: {ann_path.name}"

        ann = load_json(ann_path)
        gt = load_json(gt_path)

        pairs.append((ann_path, ann, gt_path, gt))

    return pairs


def split_total(out_root: Path) -> int:
    total = 0

    for name in ["train.txt", "val.txt", "test.txt"]:
        path = out_root / "splits" / name
        if not path.exists():
            continue

        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        total += len(lines)

    return total


def safe_ratio(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return float(num) / float(den)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def list_export_files(out_root: Path) -> list[Path]:
    exports_dir = out_root / "exports"
    if not exports_dir.exists():
        return []
    return sorted(p for p in exports_dir.rglob("*") if p.is_file())


def collect_log_text(out_root: Path) -> str:
    candidates = list(out_root.rglob("*.log")) + list(out_root.rglob("run*.txt"))

    parts: list[str] = []
    for path in candidates:
        parts.append(read_text_safe(path))

    return "\n".join(parts)


def assert_no_fatal_log_errors(out_root: Path) -> dict[str, int]:
    text = collect_log_text(out_root).lower()

    counts = {
        "traceback_count": text.count("traceback"),
        "fatal_count": text.count("fatal"),
        "memory_error_count": text.count("memoryerror"),
        "json_decode_error_count": text.count("jsondecodeerror"),
    }

    assert counts["traceback_count"] == 0, counts
    assert counts["fatal_count"] == 0, counts
    assert counts["memory_error_count"] == 0, counts
    assert counts["json_decode_error_count"] == 0, counts

    return counts