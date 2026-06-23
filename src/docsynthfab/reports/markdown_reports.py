# src/docsynthfab/reports/markdown_reports.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# This module uses only the Python standard library.

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from .io_utils import _now_utc_iso
from .label_schema import LABEL_SCHEMA_VERSION


def _fmt(x: Any) -> str:
    """Format values for Markdown tables."""
    if x is None:
        return ""

    try:
        return f"{float(x):.6g}"
    except Exception:
        return str(x)


def diversity_report_markdown(summary: Dict[str, Any]) -> str:
    """Render the diversity summary as a Markdown report."""
    lines = [
        "# Diversity Report",
        "",
        f"- Created at: `{summary.get('created_at')}`",
        f"- Page count: `{summary.get('page_count')}`",
        "",
        "## Numeric variance summary",
        "",
        "| Field | Mean | Std | Variance | Min | P50 | P95 | Max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for field, s in summary.get("numeric", {}).items():
        lines.append(
            "| {field} | {mean} | {std} | {var} | {minv} | {p50} | {p95} | {maxv} |".format(
                field=field,
                mean=_fmt(s.get("mean")),
                std=_fmt(s.get("std")),
                var=_fmt(s.get("variance")),
                minv=_fmt(s.get("min")),
                p50=_fmt(s.get("p50")),
                p95=_fmt(s.get("p95")),
                maxv=_fmt(s.get("max")),
            )
        )

    lines.extend(
        [
            "",
            "## Categorical diversity",
            "",
            "| Field | Unique | Entropy bits | Top counts |",
            "|---|---:|---:|---|",
        ]
    )

    for field, s in summary.get("categorical", {}).items():
        counts = s.get("counts", {}) or {}
        top = dict(Counter(counts).most_common(6))

        lines.append(
            f"| {field} | {s.get('unique')} | {_fmt(s.get('entropy_bits'))} | `{json.dumps(top, ensure_ascii=False)}` |"
        )

    lines.extend(
        [
            "",
            "## Joint coverage",
            "",
            "| Fields | Unique combinations | Entropy bits | Top combinations |",
            "|---|---:|---:|---|",
        ]
    )

    for name, s in summary.get("joint_coverage", {}).items():
        top = s.get("top_combinations", {}) or {}

        lines.append(
            f"| {name} | {s.get('unique_combinations')} | {_fmt(s.get('entropy_bits'))} | `{json.dumps(top, ensure_ascii=False)}` |"
        )

    lines.extend(
        [
            "",
            "## Target vs observed gap",
            "",
        ]
    )

    gap = summary.get("target_vs_observed", {}) or {}

    if not gap:
        lines.append("No config target distributions were detected for comparison.")
    else:
        for field, obj in gap.items():
            lines.append(f"### `{field}`")
            lines.append("")
            lines.append("| Value | Target | Observed | Signed gap | Abs gap |")
            lines.append("|---|---:|---:|---:|---:|")

            target = obj.get("target", {}) or {}
            observed = obj.get("observed", {}) or {}
            signed = obj.get("signed_gap", {}) or {}
            abs_gap = obj.get("abs_gap", {}) or {}

            for k in sorted(set(target) | set(observed)):
                lines.append(
                    f"| `{k}` | {_fmt(target.get(k, 0.0))} | {_fmt(observed.get(k, 0.0))} | {_fmt(signed.get(k, 0.0))} | {_fmt(abs_gap.get(k, 0.0))} |"
                )

            lines.append("")

    lines.extend(
        [
            "",
            "## Recommendations",
            "",
            "| Level | Area | Finding | Recommendation |",
            "|---|---|---|---|",
        ]
    )

    for r in summary.get("recommendations", []) or []:
        lines.append(
            f"| {r.get('level')} | {r.get('area')} | {r.get('finding')} | {r.get('recommendation')} |"
        )

    return "\n".join(lines)


def build_dataset_card(
    *,
    project_name: str,
    version: str,
    cfg_path: str,
    out_root: Path,
    pages_requested: int,
    pages_ok: int,
    pages_fail: int,
    seed: int,
    workers: int,
    splits: Dict[str, Any],
    export_targets: List[str],
) -> str:
    """Build a Markdown dataset card for the generated synthetic dataset."""
    return "\n".join(
        [
            "# Generated Dataset Card",
            "",
            "## Generator",
            "",
            f"- Project: `{project_name}`",
            f"- Version: `{version}`",
            f"- Label schema: `{LABEL_SCHEMA_VERSION}`",
            f"- Created at: `{_now_utc_iso()}`",
            "",
            "## Run",
            "",
            f"- Config path: `{cfg_path}`",
            f"- Output root: `{out_root}`",
            f"- Pages requested: `{pages_requested}`",
            f"- Pages OK: `{pages_ok}`",
            f"- Pages failed: `{pages_fail}`",
            f"- Seed: `{seed}`",
            f"- Workers: `{workers}`",
            f"- Splits: `{json.dumps(splits, ensure_ascii=False)}`",
            f"- Export targets: `{', '.join(export_targets) if export_targets else 'native'}`",
            "",
            "## Output folders",
            "",
            "- `images/`: generated page images",
            "- `masks/`: generated segmentation masks",
            "- `ann/`: full annotation JSON files",
            "- `gt/`: ground-truth export JSON files",
            "- `splits/`: train/val/test page id lists",
            "- `reports/`: schema, run manifest, feature table, and diversity report",
            "- `exports/`: model-specific export packages",
            "",
            "## Recommended uses",
            "",
            "- Synthetic OCR and Document AI experiments",
            "- Text/table/math region segmentation",
            "- Layout detection",
            "- OCR line recognition after crop export",
            "- LaTeX/math region experiments",
            "",
            "## Not recommended uses",
            "",
            "- Claiming real-world OCR quality without real validation data",
            "- Replacing domain-specific evaluation",
            "- Treating synthetic diversity as automatically useful without benchmark checks",
        ]
    )



