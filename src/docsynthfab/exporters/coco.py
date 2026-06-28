# src/docsynthfab/exporters/coco.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import all_split_ids, copy_file, read_json, reset_dir, write_json, write_text
from .schemas import COCO_CATEGORIES, COCO_CATEGORY_MAP


_COCO_README = """# COCO Export

This export converts document block boxes to COCO layout detection annotations.

## Categories

1. plain_text
2. table_region
3. math_latex
4. figure

## Structure

- `images/train|val|test/`
- `annotations/instances_train.json`
- `annotations/instances_val.json`
- `annotations/instances_test.json`
- `categories.json`
"""


def block_semantic_type(block_type: str) -> Optional[str]:
    """Map generator block types to stable semantic export classes."""
    value = str(block_type or "").lower().strip()

    if value in {"paragraph", "title", "caption", "header", "footer", "text"}:
        return "plain_text"

    if value == "table":
        return "table_region"

    if value in {"equation", "math", "latex"}:
        return "math_latex"

    if value in {"figure", "auto_figure"}:
        return "figure"

    return None


def bbox_xywh_valid(bbox: Any) -> Optional[List[float]]:
    """Validate and normalize a bbox in [x, y, w, h] format."""
    if not isinstance(bbox, list) or len(bbox) < 4:
        return None

    try:
        x, y, w, h = [float(bbox[i]) for i in range(4)]
    except Exception:
        return None

    if w <= 0 or h <= 0:
        return None

    return [x, y, w, h]


def coco_image_obj(pid: str, ann: Dict[str, Any], image_id: int) -> Dict[str, Any]:
    """Create a COCO image object from one page annotation."""
    size = ann.get("size", {}) or {}

    return {
        "id": image_id,
        "file_name": f"{pid}.png",
        "width": int(size.get("w", 0) or 0),
        "height": int(size.get("h", 0) or 0),
    }


def coco_annotations_for_page(
    ann: Dict[str, Any],
    image_id: int,
    start_ann_id: int,
) -> Tuple[List[Dict[str, Any]], int]:
    """Convert generator block boxes into COCO annotations for one page."""
    out: List[Dict[str, Any]] = []
    ann_id = start_ann_id

    for block in ann.get("blocks", []) or []:
        semantic = block_semantic_type(str(block.get("block_type", "")))

        if semantic is None:
            continue

        category_id = COCO_CATEGORY_MAP.get(semantic)

        if category_id is None:
            continue

        bbox = bbox_xywh_valid(block.get("bbox"))

        if bbox is None:
            continue

        x, y, w, h = bbox

        out.append(
            {
                "id": ann_id,
                "image_id": image_id,
                "category_id": category_id,
                "bbox": [x, y, w, h],
                "area": float(w * h),
                "iscrowd": 0,
                "segmentation": [],
                "metadata": {
                    "block_id": block.get("block_id"),
                    "block_type": block.get("block_type"),
                    "semantic_type": semantic,
                },
            }
        )

        ann_id += 1

    return out, ann_id


def export_coco(out_root: Path) -> Dict[str, Any]:
    """Export block-level layout boxes in COCO detection format."""
    out_root = Path(out_root)
    export_root = out_root / "exports" / "coco"

    reset_dir(export_root)

    splits = all_split_ids(out_root)
    summary: Dict[str, Dict[str, int]] = {}

    for split, ids in splits.items():
        images: List[Dict[str, Any]] = []
        annotations: List[Dict[str, Any]] = []
        annotation_id = 1

        for image_id, pid in enumerate(ids, start=1):
            ann_path = out_root / "ann" / f"{pid}.json"
            img_src = out_root / "images" / f"{pid}.png"
            img_dst = export_root / "images" / split / f"{pid}.png"

            if not ann_path.exists():
                continue

            ann = read_json(ann_path)

            images.append(coco_image_obj(pid, ann, image_id))

            page_annotations, annotation_id = coco_annotations_for_page(
                ann=ann,
                image_id=image_id,
                start_ann_id=annotation_id,
            )

            annotations.extend(page_annotations)
            copy_file(img_src, img_dst)

        coco_obj = {
            "info": {
                "description": "Synthetic Document AI COCO export",
                "version": "coco-export-v1",
            },
            "licenses": [],
            "images": images,
            "annotations": annotations,
            "categories": COCO_CATEGORIES,
        }

        write_json(export_root / "annotations" / f"instances_{split}.json", coco_obj)

        summary[split] = {
            "images": len(images),
            "annotations": len(annotations),
        }

    write_json(export_root / "categories.json", COCO_CATEGORIES)
    write_text(export_root / "README.md", _COCO_README)

    return {
        "target": "coco",
        "export_root": str(export_root),
        "summary": summary,
    }



