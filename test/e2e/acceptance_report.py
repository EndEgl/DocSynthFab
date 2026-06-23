# test/e2e/acceptance_report.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def artifact_root(project_root: Path) -> Path:
    root = project_root / "test_artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def append_metric_record(
    *,
    project_root: Path,
    test_name: str,
    metrics: Dict[str, Any],
) -> None:
    root = artifact_root(project_root)
    path = root / "e2e_metrics.jsonl"

    record = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "test_name": test_name,
        "metrics": metrics,
    }

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_acceptance_report(
    *,
    project_root: Path,
    suite_name: str,
    metrics: Dict[str, Any],
) -> dict[str, Any]:
    root = artifact_root(project_root)

    report = {
        "suite": suite_name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decision": metrics.get("decision", "UNKNOWN"),
        "scores": metrics,
    }

    json_path = root / "acceptance_quality_report.json"
    md_path = root / "acceptance_quality_report.md"

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    md = [
        "# DocSynthFab Acceptance Quality Report",
        "",
        f"- Suite: `{suite_name}`",
        f"- Decision: **{report['decision']}**",
        f"- Overall acceptance score: `{metrics.get('overall_acceptance_score', 0.0):.4f}`",
        f"- Package score: `{metrics.get('package_score', 0.0):.4f}`",
        f"- Manifest score: `{metrics.get('manifest_score', 0.0):.4f}`",
        f"- BBox valid ratio: `{metrics.get('bbox_valid_ratio', 0.0):.4f}`",
        f"- ANN/GT text match ratio: `{metrics.get('ann_gt_text_match_ratio', 0.0):.4f}`",
        f"- Text mask bbox hit ratio: `{metrics.get('text_mask_bbox_hit_ratio', 0.0):.4f}`",
        f"- Math mask bbox hit ratio: `{metrics.get('math_mask_bbox_hit_ratio', 0.0):.4f}`",
        f"- Export score: `{metrics.get('export_score', 0.0):.4f}`",
        f"- Diversity score: `{metrics.get('diversity_score', 0.0):.4f}`",
        "",
        "## Raw metric keys",
        "",
    ]

    for key in sorted(metrics):
        value = metrics[key]
        if isinstance(value, (dict, list)):
            continue
        md.append(f"- `{key}`: `{value}`")

    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    return report



