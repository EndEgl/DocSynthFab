# src/ai1_gen/exporters/segformer.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .common import all_split_ids, copy_file, reset_dir, write_json, write_text
from .schemas import CLASS_MAP


_SEGFORMER_README = """# SegFormer / U-Net Export

This export prepares image and mask folders by split.

## Structure

- `images/train|val|test/`
- `masks_text/train|val|test/`
- `masks_math/train|val|test/`
- `class_map.json`

## Current phase

This first export preserves the existing binary masks:

- text mask
- math/LaTeX mask

A later phase can create a single multi-class semantic mask:

- 0 background
- 1 plain_text
- 2 table_region
- 3 math_latex
- 4 figure
"""


def export_segformer(out_root: Path) -> Dict[str, Any]:
    """Export split-based image and binary mask folders for segmentation training."""
    out_root = Path(out_root)
    export_root = out_root / "exports" / "segformer"

    reset_dir(export_root)

    splits = all_split_ids(out_root)

    copied = {
        "images": 0,
        "mask_text": 0,
        "mask_math": 0,
    }

    missing = {
        "images": 0,
        "mask_text": 0,
        "mask_math": 0,
    }

    for split, ids in splits.items():
        for pid in ids:
            img_src = out_root / "images" / f"{pid}.png"
            text_mask_src = out_root / "masks" / f"{pid}_mask_text.png"
            math_mask_src = out_root / "masks" / f"{pid}_mask_math.png"

            img_dst = export_root / "images" / split / f"{pid}.png"
            text_dst = export_root / "masks_text" / split / f"{pid}.png"
            math_dst = export_root / "masks_math" / split / f"{pid}.png"

            if copy_file(img_src, img_dst):
                copied["images"] += 1
            else:
                missing["images"] += 1

            if copy_file(text_mask_src, text_dst):
                copied["mask_text"] += 1
            else:
                missing["mask_text"] += 1

            if copy_file(math_mask_src, math_dst):
                copied["mask_math"] += 1
            else:
                missing["mask_math"] += 1

    write_json(
        export_root / "class_map.json",
        {
            "format": "segformer-export-v1",
            "phase": "binary-mask-split-export",
            "classes": CLASS_MAP,
            "available_masks": {
                "masks_text": "binary text mask",
                "masks_math": "binary math/latex mask",
            },
            "note": (
                "This first export preserves existing binary masks. "
                "Multi-class semantic mask export will be added later."
            ),
        },
    )

    write_text(export_root / "README.md", _SEGFORMER_README)

    return {
        "target": "segformer",
        "export_root": str(export_root),
        "copied": copied,
        "missing": missing,
        "splits": {k: len(v) for k, v in splits.items()},
    }