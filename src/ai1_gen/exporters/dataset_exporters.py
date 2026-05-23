# src/ai1_gen/exporters/dataset_exporters.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
#
# İlk export hedefleri:
# - native
# - segformer
# - coco
#
# Not:
# - Native export, mevcut output klasörlerini paketler.
# - SegFormer export, split bazlı image + mask klasörleri üretir.
# - COCO export, block bbox'ları layout detection formatına çevirir.

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


CLASS_MAP: Dict[int, str] = {
    0: "background",
    1: "plain_text",
    2: "table_region",
    3: "math_latex",
    4: "figure",
}

COCO_CATEGORY_MAP: Dict[str, int] = {
    "plain_text": 1,
    "table_region": 2,
    "math_latex": 3,
    "figure": 4,
}


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _copy_file(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _read_split_ids(splits_dir: Path, split: str) -> List[str]:
    p = splits_dir / f"{split}.txt"
    if not p.exists():
        return []
    return [x.strip() for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _all_split_ids(out_root: Path) -> Dict[str, List[str]]:
    splits_dir = out_root / "splits"
    return {
        "train": _read_split_ids(splits_dir, "train"),
        "val": _read_split_ids(splits_dir, "val"),
        "test": _read_split_ids(splits_dir, "test"),
    }


def _block_semantic_type(block_type: str) -> Optional[str]:
    bt = str(block_type or "").lower().strip()

    if bt in {"paragraph", "title", "caption", "header", "footer", "text"}:
        return "plain_text"
    if bt == "table":
        return "table_region"
    if bt in {"equation", "math", "latex"}:
        return "math_latex"
    if bt in {"figure", "auto_figure"}:
        return "figure"

    return None


def _bbox_xywh_valid(bbox: Any) -> Optional[List[float]]:
    if not isinstance(bbox, list) or len(bbox) < 4:
        return None

    try:
        x, y, w, h = [float(bbox[i]) for i in range(4)]
    except Exception:
        return None

    if w <= 0 or h <= 0:
        return None

    return [x, y, w, h]


def export_native(out_root: Path) -> Dict[str, Any]:
    """
    Native export:
    Mevcut dataset output'unu exports/native altına kopyalar.
    Bu format tüm generator metadata'sını korur.
    """
    out_root = Path(out_root)
    export_root = out_root / "exports" / "native"
    export_root.mkdir(parents=True, exist_ok=True)

    copied_dirs: List[str] = []

    for name in ("images", "masks", "ann", "gt", "splits"):
        src_dir = out_root / name
        dst_dir = export_root / name

        if dst_dir.exists():
            shutil.rmtree(dst_dir)

        if src_dir.exists():
            shutil.copytree(src_dir, dst_dir)
            copied_dirs.append(name)

    _copy_file(out_root / "reports" / "label_schema.json", export_root / "label_schema.json")
    _copy_file(out_root / "reports" / "dataset_card.md", export_root / "dataset_card.md")
    _copy_file(out_root / "reports" / "run_manifest.json", export_root / "run_manifest.json")

    readme = """# Native Export

This folder contains the generator-native dataset package.

## Contents

- `images/`: generated page images
- `masks/`: generated text/math masks
- `ann/`: full annotation JSON files
- `gt/`: ground-truth export JSON files
- `splits/`: train/val/test page id lists
- `label_schema.json`: class and task schema

Use this format if you want maximum access to all generator metadata.
"""
    _write_text(export_root / "README.md", readme)

    return {
        "target": "native",
        "export_root": str(export_root),
        "copied_dirs": copied_dirs,
    }


def export_segformer(out_root: Path) -> Dict[str, Any]:
    """
    İlk SegFormer/U-Net export:
    - images/{split}/ içine sayfa görselleri kopyalanır.
    - masks_text/{split}/ içine binary text mask kopyalanır.
    - masks_math/{split}/ içine binary math mask kopyalanır.

    Bu ilk fazda multi-class tek mask üretmiyoruz.
    Kalite/özelleştirme turunda şunu ekleyeceğiz:
    - 0 background
    - 1 plain_text
    - 2 table_region
    - 3 math_latex
    - 4 figure
    """
    out_root = Path(out_root)
    export_root = out_root / "exports" / "segformer"

    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True, exist_ok=True)

    splits = _all_split_ids(out_root)

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

            if _copy_file(img_src, img_dst):
                copied["images"] += 1
            else:
                missing["images"] += 1

            if _copy_file(text_mask_src, text_dst):
                copied["mask_text"] += 1
            else:
                missing["mask_text"] += 1

            if _copy_file(math_mask_src, math_dst):
                copied["mask_math"] += 1
            else:
                missing["mask_math"] += 1

    _write_json(
        export_root / "class_map.json",
        {
            "format": "segformer-export-v1",
            "phase": "binary-mask-split-export",
            "classes": CLASS_MAP,
            "available_masks": {
                "masks_text": "binary text mask",
                "masks_math": "binary math/latex mask",
            },
            "note": "This first export preserves existing binary masks. Multi-class semantic mask export will be added in the quality/customization phase.",
        },
    )

    readme = """# SegFormer / U-Net Export

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
    _write_text(export_root / "README.md", readme)

    return {
        "target": "segformer",
        "export_root": str(export_root),
        "copied": copied,
        "missing": missing,
        "splits": {k: len(v) for k, v in splits.items()},
    }


def _coco_image_obj(pid: str, ann: Dict[str, Any], image_id: int) -> Dict[str, Any]:
    size = ann.get("size", {}) or {}
    return {
        "id": image_id,
        "file_name": f"{pid}.png",
        "width": int(size.get("w", 0) or 0),
        "height": int(size.get("h", 0) or 0),
    }


def _coco_annotations_for_page(
    ann: Dict[str, Any],
    image_id: int,
    start_ann_id: int,
) -> Tuple[List[Dict[str, Any]], int]:
    out: List[Dict[str, Any]] = []
    ann_id = start_ann_id

    for b in ann.get("blocks", []) or []:
        semantic = _block_semantic_type(str(b.get("block_type", "")))
        if semantic is None:
            continue

        cat_id = COCO_CATEGORY_MAP.get(semantic)
        if cat_id is None:
            continue

        bbox = _bbox_xywh_valid(b.get("bbox"))
        if bbox is None:
            continue

        x, y, w, h = bbox

        out.append(
            {
                "id": ann_id,
                "image_id": image_id,
                "category_id": cat_id,
                "bbox": [x, y, w, h],
                "area": float(w * h),
                "iscrowd": 0,
                "segmentation": [],
                "metadata": {
                    "block_id": b.get("block_id"),
                    "block_type": b.get("block_type"),
                    "semantic_type": semantic,
                },
            }
        )
        ann_id += 1

    return out, ann_id


def export_coco(out_root: Path) -> Dict[str, Any]:
    """
    COCO layout detection export.

    Blocks üzerinden şu kategoriler üretilir:
    - plain_text
    - table_region
    - math_latex
    - figure
    """
    out_root = Path(out_root)
    export_root = out_root / "exports" / "coco"

    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True, exist_ok=True)

    splits = _all_split_ids(out_root)

    categories = [
        {"id": 1, "name": "plain_text", "supercategory": "document"},
        {"id": 2, "name": "table_region", "supercategory": "document"},
        {"id": 3, "name": "math_latex", "supercategory": "document"},
        {"id": 4, "name": "figure", "supercategory": "document"},
    ]

    summary: Dict[str, Dict[str, int]] = {}

    for split, ids in splits.items():
        images: List[Dict[str, Any]] = []
        annotations: List[Dict[str, Any]] = []
        ann_id = 1

        for image_idx, pid in enumerate(ids, start=1):
            ann_path = out_root / "ann" / f"{pid}.json"
            img_src = out_root / "images" / f"{pid}.png"
            img_dst = export_root / "images" / split / f"{pid}.png"

            if not ann_path.exists():
                continue

            ann = _read_json(ann_path)
            images.append(_coco_image_obj(pid, ann, image_idx))

            page_anns, ann_id = _coco_annotations_for_page(
                ann=ann,
                image_id=image_idx,
                start_ann_id=ann_id,
            )
            annotations.extend(page_anns)

            _copy_file(img_src, img_dst)

        coco_obj = {
            "info": {
                "description": "Synthetic Document AI COCO export",
                "version": "coco-export-v1",
            },
            "licenses": [],
            "images": images,
            "annotations": annotations,
            "categories": categories,
        }

        _write_json(export_root / "annotations" / f"instances_{split}.json", coco_obj)

        summary[split] = {
            "images": len(images),
            "annotations": len(annotations),
        }

    _write_json(export_root / "categories.json", categories)

    readme = """# COCO Export

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
    _write_text(export_root / "README.md", readme)

    return {
        "target": "coco",
        "export_root": str(export_root),
        "summary": summary,
    }


def export_dataset_package(
    *,
    out_root: Path,
    targets: Sequence[str],
) -> Dict[str, Any]:
    """
    Ana export dispatcher.
    """
    out_root = Path(out_root)
    (out_root / "exports").mkdir(parents=True, exist_ok=True)

    normalized = [str(t).strip().lower() for t in targets if str(t).strip()]
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

    _write_json(out_root / "exports" / "export_summary.json", results)
    return results