# src/docsynthfab/exporters/dataset_exporters.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Sequence

from .coco import export_coco
from .common import write_json
from .native import export_native
from .segformer import export_segformer


def export_dataset_package(
    *,
    out_root: Path,
    targets: Sequence[str],
) -> Dict[str, Any]:
    """Export a generated dataset package into one or more target formats."""
    out_root = Path(out_root)
    (out_root / "exports").mkdir(parents=True, exist_ok=True)

    normalized = [
        str(target).strip().lower()
        for target in targets
        if str(target).strip()
    ]

    if not normalized:
        normalized = ["native"]

    results: Dict[str, Any] = {}

    for target in normalized:
        if target == "native":
            results["native"] = export_native(out_root)
        elif target == "segformer":
            results["segformer"] = export_segformer(out_root)
        elif target == "coco":
            results["coco"] = export_coco(out_root)
        else:
            results[target] = {
                "target": target,
                "skipped": True,
                "reason": "unsupported-export-target",
            }

    write_json(out_root / "exports" / "export_summary.json", results)
    return results



