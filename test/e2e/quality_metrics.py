# test/e2e/quality_metrics.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12
# - numpy>=1.24,<3.0

from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict

import numpy as np
from PIL import Image

from e2e_support import (
    clamp01,
    json_files,
    list_export_files,
    load_ann_gt_pairs,
    load_json,
    png_files,
    required_output_dirs,
    required_report_files,
    safe_ratio,
    split_total,
)


def _open_mask_array(path: Path) -> np.ndarray:
    img = Image.open(path).convert("L")
    return np.array(img)


def _mask_candidates_for_page(out_root: Path, page_stem: str, kind: str) -> list[Path]:
    masks_dir = out_root / "masks"

    if not masks_dir.exists():
        return []

    kind = kind.lower()
    candidates: list[Path] = []

    for path in masks_dir.rglob("*.png"):
        name = path.name.lower()
        stem = path.stem.lower()

        if page_stem.lower() not in stem:
            continue

        if kind in {"text", "mask_text"} and ("text" in name or "txt" in name):
            candidates.append(path)

        if kind in {"math", "mask_math"} and ("math" in name or "latex" in name or "equation" in name):
            candidates.append(path)

    return sorted(candidates)


def _bbox_inside_page(bbox: Any, page_w: int, page_h: int) -> bool:
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False

    try:
        x, y, w, h = [float(v) for v in bbox]
    except Exception:
        return False

    if w <= 0 or h <= 0:
        return False

    if x < 0 or y < 0:
        return False

    if x >= page_w or y >= page_h:
        return False

    if x + w > page_w or y + h > page_h:
        return False

    return True


def _bbox_mask_hit(mask: np.ndarray, bbox: Any) -> tuple[bool, float]:
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False, 0.0

    try:
        x, y, w, h = [int(round(float(v))) for v in bbox]
    except Exception:
        return False, 0.0

    H, W = mask.shape[:2]

    x0 = max(0, min(W, x))
    y0 = max(0, min(H, y))
    x1 = max(0, min(W, x + max(1, w)))
    y1 = max(0, min(H, y + max(1, h)))

    if x1 <= x0 or y1 <= y0:
        return False, 0.0

    crop = mask[y0:y1, x0:x1]
    area = float(crop.size)
    nonzero = float(np.count_nonzero(crop > 0))

    return nonzero > 0, safe_ratio(nonzero, area)


def measure_output_package(out_root: Path) -> dict[str, Any]:
    dirs_found = 0
    for dirname in required_output_dirs():
        if (out_root / dirname).exists():
            dirs_found += 1

    files_found = 0
    for filename in required_report_files():
        if (out_root / "reports" / filename).exists():
            files_found += 1

    images = sorted((out_root / "images").glob("*.png"))
    anns = sorted((out_root / "ann").glob("*.json"))
    gts = sorted((out_root / "gt").glob("*.json"))

    split_count = split_total(out_root)

    score = min(
        safe_ratio(dirs_found, len(required_output_dirs())),
        safe_ratio(files_found, len(required_report_files())),
        1.0 if images and len(images) == len(anns) == len(gts) else 0.0,
    )

    return {
        "required_dirs_found": dirs_found,
        "required_dirs_total": len(required_output_dirs()),
        "required_dirs_found_ratio": safe_ratio(dirs_found, len(required_output_dirs())),
        "required_files_found": files_found,
        "required_files_total": len(required_report_files()),
        "required_files_found_ratio": safe_ratio(files_found, len(required_report_files())),
        "image_count": len(images),
        "ann_count": len(anns),
        "gt_count": len(gts),
        "split_total": split_count,
        "package_score": float(score),
    }


def measure_manifest_contract(out_root: Path) -> dict[str, Any]:
    manifest_path = out_root / "reports" / "run_manifest.json"
    manifest = load_json(manifest_path)

    required = [
        "manifest_version",
        "version",
        "run_id",
        "project_name",
        "generator_version",
        "label_schema_version",
        "created_at",
        "config_path",
        "out_root",
        "pages_requested",
        "pages_ok",
        "pages_fail",
        "seed",
        "workers",
        "splits",
        "export_targets",
        "outputs",
        "qc_summary",
    ]

    present = [key for key in required if key in manifest]

    return {
        "manifest_required_fields": len(required),
        "manifest_present_fields": len(present),
        "manifest_fields_present_ratio": safe_ratio(len(present), len(required)),
        "has_run_id": bool(manifest.get("run_id")),
        "has_created_at": bool(manifest.get("created_at")),
        "has_generator_version": bool(manifest.get("generator_version")),
        "has_export_targets": isinstance(manifest.get("export_targets"), list),
        "pages_requested": int(manifest.get("pages_requested", 0)),
        "pages_ok": int(manifest.get("pages_ok", 0)),
        "pages_fail": int(manifest.get("pages_fail", 0)),
        "manifest_score": safe_ratio(len(present), len(required)),
    }


def measure_bbox_validity(out_root: Path) -> dict[str, Any]:
    total = 0
    valid = 0
    invalid: list[dict[str, Any]] = []

    for ann_path, ann, _gt_path, _gt in load_ann_gt_pairs(out_root):
        size = ann.get("size") or {}
        page_w = int(size.get("w", 0))
        page_h = int(size.get("h", 0))

        for kind in ("blocks", "lines"):
            for index, item in enumerate(ann.get(kind, []) or []):
                total += 1
                bbox = item.get("bbox")

                if _bbox_inside_page(bbox, page_w, page_h):
                    valid += 1
                else:
                    invalid.append(
                        {
                            "file": ann_path.name,
                            "kind": kind,
                            "index": index,
                            "bbox": bbox,
                            "page_w": page_w,
                            "page_h": page_h,
                        }
                    )

    return {
        "total_bboxes": total,
        "valid_bboxes": valid,
        "invalid_bboxes_count": len(invalid),
        "bbox_valid_ratio": safe_ratio(valid, total),
        "invalid_bboxes": invalid[:25],
    }


def measure_ann_gt_alignment(out_root: Path) -> dict[str, Any]:
    pairs = load_ann_gt_pairs(out_root)

    page_id_matches = 0
    line_count_compatible = 0
    text_line_matches = 0
    text_line_total = 0
    page_similarities: list[float] = []

    for _ann_path, ann, _gt_path, gt in pairs:
        if str(ann.get("page_id")) == str(gt.get("page_id")):
            page_id_matches += 1

        ann_lines = ann.get("lines", []) or []
        gt_lines = gt.get("lines", []) or []

        if ann_lines and gt_lines and abs(len(ann_lines) - len(gt_lines)) <= max(2, int(0.25 * len(ann_lines))):
            line_count_compatible += 1

        ann_texts: list[str] = []
        for line in ann_lines:
            text = (
                line.get("gt_text")
                or line.get("text")
                or line.get("latex")
                or line.get("gt_latex")
                or ""
            )
            text = str(text).strip()
            if text:
                ann_texts.append(text)

        gt_texts: list[str] = []
        for line in gt_lines:
            text = (
                line.get("text")
                or line.get("gt_text")
                or line.get("latex")
                or line.get("gt_latex")
                or ""
            )
            text = str(text).strip()
            if text:
                gt_texts.append(text)

        gt_joined = "\n".join(gt_texts) or str(gt.get("page_text", ""))
        ann_joined = "\n".join(ann_texts)

        if ann_joined or gt_joined:
            page_similarities.append(SequenceMatcher(None, ann_joined, gt_joined).ratio())

        gt_blob = "\n".join(gt_texts) + "\n" + str(gt.get("page_text", ""))

        for text in ann_texts:
            text_line_total += 1
            if text in gt_blob:
                text_line_matches += 1

    return {
        "pages_checked": len(pairs),
        "page_id_match_ratio": safe_ratio(page_id_matches, len(pairs)),
        "line_count_compatible_ratio": safe_ratio(line_count_compatible, len(pairs)),
        "ann_gt_text_match_ratio": safe_ratio(text_line_matches, text_line_total),
        "page_text_similarity_mean": float(np.mean(page_similarities)) if page_similarities else 0.0,
        "text_lines_checked": text_line_total,
        "text_lines_matched": text_line_matches,
    }


def measure_mask_bbox_alignment(out_root: Path) -> dict[str, Any]:
    text_checked = 0
    text_hit = 0
    text_coverages: list[float] = []

    math_checked = 0
    math_hit = 0
    math_coverages: list[float] = []

    for ann_path, ann, _gt_path, _gt in load_ann_gt_pairs(out_root):
        stem = ann_path.stem

        text_masks = _mask_candidates_for_page(out_root, stem, "text")
        math_masks = _mask_candidates_for_page(out_root, stem, "math")

        text_mask = _open_mask_array(text_masks[0]) if text_masks else None
        math_mask = _open_mask_array(math_masks[0]) if math_masks else None

        for line in ann.get("lines", []) or []:
            line_type = str(line.get("line_type", "text")).lower()
            bbox = line.get("bbox")

            is_math = line_type in {"math", "latex", "equation"} or bool(line.get("latex") or line.get("gt_latex"))

            if is_math:
                if math_mask is None:
                    continue
                math_checked += 1
                hit, coverage = _bbox_mask_hit(math_mask, bbox)
                math_hit += int(hit)
                math_coverages.append(float(coverage))
            else:
                if text_mask is None:
                    continue
                text_checked += 1
                hit, coverage = _bbox_mask_hit(text_mask, bbox)
                text_hit += int(hit)
                text_coverages.append(float(coverage))

    return {
        "text_lines_checked": text_checked,
        "text_lines_with_mask_hit": text_hit,
        "text_mask_bbox_hit_ratio": safe_ratio(text_hit, text_checked),
        "text_mask_coverage_mean": float(np.mean(text_coverages)) if text_coverages else 0.0,
        "math_lines_checked": math_checked,
        "math_lines_with_mask_hit": math_hit,
        "math_mask_bbox_hit_ratio": safe_ratio(math_hit, math_checked) if math_checked else 1.0,
        "math_mask_coverage_mean": float(np.mean(math_coverages)) if math_coverages else 0.0,
    }


def measure_feature_mode_ratios(out_root: Path) -> dict[str, Any]:
    pages = 0
    pages_with_table = 0
    pages_with_equation = 0

    text_lines = 0
    math_lines = 0
    table_blocks = 0
    total_lines = 0
    total_blocks = 0

    table_area_ratios: list[float] = []
    text_mask_ratios: list[float] = []
    math_mask_ratios: list[float] = []

    for ann_path, ann, _gt_path, _gt in load_ann_gt_pairs(out_root):
        pages += 1
        meta = ann.get("meta", {}) or {}
        size = ann.get("size", {}) or {}

        page_w = int(size.get("w", 0))
        page_h = int(size.get("h", 0))
        page_area = max(1, page_w * page_h)

        if bool(meta.get("has_table")):
            pages_with_table += 1

        if bool(meta.get("has_equation") or meta.get("has_equation_layout")):
            pages_with_equation += 1

        text_mask_ratios.append(safe_ratio(float(meta.get("mask_text_nonzero", 0)), page_area))
        math_mask_ratios.append(safe_ratio(float(meta.get("mask_math_nonzero", 0)), page_area))

        for line in ann.get("lines", []) or []:
            total_lines += 1
            lt = str(line.get("line_type", "text")).lower()
            if lt in {"math", "latex", "equation"} or line.get("latex") or line.get("gt_latex"):
                math_lines += 1
            else:
                text_lines += 1

        for block in ann.get("blocks", []) or []:
            total_blocks += 1
            bt = str(block.get("block_type", "")).lower()
            if bt == "table":
                table_blocks += 1
                bbox = block.get("bbox") or [0, 0, 0, 0]
                try:
                    area = float(bbox[2]) * float(bbox[3])
                    table_area_ratios.append(safe_ratio(area, page_area))
                except Exception:
                    pass

    return {
        "pages": pages,
        "pages_with_table": pages_with_table,
        "pages_with_equation": pages_with_equation,
        "table_presence_ratio": safe_ratio(pages_with_table, pages),
        "latex_presence_ratio": safe_ratio(pages_with_equation, pages),
        "text_line_ratio": safe_ratio(text_lines, total_lines),
        "math_line_ratio": safe_ratio(math_lines, total_lines),
        "table_block_ratio": safe_ratio(table_blocks, total_blocks),
        "table_area_ratio_mean": float(np.mean(table_area_ratios)) if table_area_ratios else 0.0,
        "text_mask_ratio_mean": float(np.mean(text_mask_ratios)) if text_mask_ratios else 0.0,
        "math_mask_ratio_mean": float(np.mean(math_mask_ratios)) if math_mask_ratios else 0.0,
    }


def measure_export_quality(out_root: Path) -> dict[str, Any]:
    export_files = list_export_files(out_root)

    json_export_files = [p for p in export_files if p.suffix.lower() == ".json"]
    parse_ok = 0

    coco_valid = False
    coco_images = 0
    coco_annotations = 0
    coco_categories = 0

    for path in json_export_files:
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            parse_ok += 1

            if isinstance(obj, dict) and {"images", "annotations", "categories"} <= set(obj):
                coco_valid = True
                coco_images = len(obj.get("images") or [])
                coco_annotations = len(obj.get("annotations") or [])
                coco_categories = len(obj.get("categories") or [])

        except Exception:
            pass

    segformer_like_masks = [
        p for p in export_files
        if p.suffix.lower() in {".png", ".jpg", ".jpeg"} and "seg" in str(p).lower()
    ]

    native_like = [
        p for p in export_files
        if p.suffix.lower() in {".json", ".jsonl", ".csv"}
    ]

    export_score = min(
        1.0 if export_files else 0.0,
        safe_ratio(parse_ok, len(json_export_files)) if json_export_files else 1.0,
    )

    return {
        "export_files_count": len(export_files),
        "json_export_files_count": len(json_export_files),
        "json_export_parse_ok": parse_ok,
        "json_export_parse_ratio": safe_ratio(parse_ok, len(json_export_files)) if json_export_files else 1.0,
        "native_export_valid": bool(native_like),
        "coco_export_valid": bool(coco_valid),
        "coco_images": coco_images,
        "coco_annotations": coco_annotations,
        "coco_categories": coco_categories,
        "segformer_masks": len(segformer_like_masks),
        "segformer_export_valid": bool(segformer_like_masks) or bool(export_files),
        "export_score": float(export_score),
    }


def measure_diversity_summary(out_root: Path) -> dict[str, Any]:
    path = out_root / "reports" / "diversity_summary.json"

    if not path.exists():
        return {
            "diversity_summary_exists": False,
            "diversity_score": 0.0,
        }

    obj = load_json(path)

    page_count = int(obj.get("page_count", 0) or 0)

    # Generic structural scoring because diversity summary may evolve.
    numeric_count = 0
    categorical_count = 0

    def walk(x: Any) -> None:
        nonlocal numeric_count, categorical_count

        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, (int, float)):
            numeric_count += 1
        elif isinstance(x, str):
            categorical_count += 1

    walk(obj)

    diversity_score = clamp01(
        0.25 * (1.0 if page_count > 0 else 0.0)
        + 0.50 * min(1.0, numeric_count / 10.0)
        + 0.25 * min(1.0, categorical_count / 5.0)
    )

    return {
        "diversity_summary_exists": True,
        "page_count": page_count,
        "numeric_metrics_count": numeric_count,
        "categorical_metrics_count": categorical_count,
        "diversity_score": diversity_score,
    }


def measure_all_core_metrics(out_root: Path) -> dict[str, Any]:
    metrics: dict[str, Any] = {}

    for block in [
        measure_output_package(out_root),
        measure_manifest_contract(out_root),
        measure_bbox_validity(out_root),
        measure_ann_gt_alignment(out_root),
        measure_mask_bbox_alignment(out_root),
        measure_feature_mode_ratios(out_root),
        measure_export_quality(out_root),
        measure_diversity_summary(out_root),
    ]:
        metrics.update(block)

    # Composite starter score. Later we can make this profile-aware.
    weighted = {
        "package_score": 0.10,
        "manifest_score": 0.08,
        "bbox_valid_ratio": 0.15,
        "ann_gt_text_match_ratio": 0.15,
        "text_mask_bbox_hit_ratio": 0.12,
        "math_mask_bbox_hit_ratio": 0.08,
        "export_score": 0.12,
        "diversity_score": 0.10,
        "table_presence_ratio": 0.05,
        "latex_presence_ratio": 0.05,
    }

    total_w = 0.0
    score = 0.0

    for key, w in weighted.items():
        if key in metrics:
            score += clamp01(float(metrics.get(key) or 0.0)) * w
            total_w += w

    metrics["overall_acceptance_score"] = safe_ratio(score, total_w)

    hard_gates_pass = (
        metrics.get("package_score", 0.0) >= 1.0
        and metrics.get("manifest_score", 0.0) >= 1.0
        and metrics.get("bbox_valid_ratio", 0.0) >= 1.0
        and metrics.get("export_score", 0.0) >= 0.95
    )

    metrics["hard_gates_pass"] = bool(hard_gates_pass)
    metrics["decision"] = "PASS" if hard_gates_pass and metrics["overall_acceptance_score"] >= 0.75 else "FAIL"

    return metrics

# ---------------------------------------------------------------------------
# Mathematical diversity metrics
# ---------------------------------------------------------------------------

def _entropy_from_counts(counts: list[int]) -> float:
    values = [float(c) for c in counts if c > 0]
    total = sum(values)

    if total <= 0:
        return 0.0

    probs = [v / total for v in values]
    return float(-sum(p * np.log2(p) for p in probs if p > 0))


def _normalized_entropy_from_counts(counts: list[int]) -> float:
    active = sum(1 for c in counts if c > 0)

    if active <= 1:
        return 0.0

    entropy = _entropy_from_counts(counts)
    max_entropy = np.log2(active)

    return safe_ratio(entropy, max_entropy)


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.std(np.asarray(values, dtype=np.float64)))


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _layout_signature_for_page(ann: dict[str, Any]) -> str:
    """
    Coarse layout signature.

    This intentionally quantizes numeric values so that small random pixel
    differences do not create fake uniqueness.
    """
    size = ann.get("size") or {}
    page_w = max(1, int(size.get("w", 1) or 1))
    page_h = max(1, int(size.get("h", 1) or 1))

    blocks = ann.get("blocks", []) or []
    lines = ann.get("lines", []) or []

    text_lines = 0
    math_lines = 0
    table_blocks = 0

    x_bins: list[int] = []
    y_bins: list[int] = []
    area_bins: list[int] = []

    for line in lines:
        lt = str(line.get("line_type", "text")).lower()
        is_math = lt in {"math", "latex", "equation"} or bool(line.get("latex") or line.get("gt_latex"))

        if is_math:
            math_lines += 1
        else:
            text_lines += 1

        bbox = line.get("bbox") or [0, 0, 0, 0]
        try:
            x, y, w, h = [float(v) for v in bbox]
        except Exception:
            continue

        x_bins.append(int((x / page_w) * 5))
        y_bins.append(int((y / page_h) * 5))
        area_bins.append(int(((w * h) / max(1, page_w * page_h)) * 100))

    for block in blocks:
        bt = str(block.get("block_type", "")).lower()
        if bt == "table":
            table_blocks += 1

    return "|".join(
        [
            f"blocks:{len(blocks)}",
            f"lines:{len(lines) // 5 * 5}",
            f"text:{text_lines // 5 * 5}",
            f"math:{math_lines}",
            f"tables:{table_blocks}",
            f"x:{','.join(map(str, sorted(set(x_bins))))}",
            f"y:{','.join(map(str, sorted(set(y_bins))))}",
            f"area:{','.join(map(str, sorted(set(area_bins))))}",
        ]
    )


def _page_feature_vector(ann: dict[str, Any]) -> list[float]:
    size = ann.get("size") or {}
    meta = ann.get("meta") or {}

    page_w = max(1, int(size.get("w", 1) or 1))
    page_h = max(1, int(size.get("h", 1) or 1))
    page_area = max(1, page_w * page_h)

    blocks = ann.get("blocks", []) or []
    lines = ann.get("lines", []) or []

    text_lines = 0
    math_lines = 0
    table_blocks = 0

    bbox_x: list[float] = []
    bbox_y: list[float] = []
    bbox_w: list[float] = []
    bbox_h: list[float] = []
    bbox_area_ratio: list[float] = []

    table_area_ratio = 0.0

    for line in lines:
        lt = str(line.get("line_type", "text")).lower()
        is_math = lt in {"math", "latex", "equation"} or bool(line.get("latex") or line.get("gt_latex"))

        if is_math:
            math_lines += 1
        else:
            text_lines += 1

        bbox = line.get("bbox") or [0, 0, 0, 0]
        try:
            x, y, w, h = [float(v) for v in bbox]
        except Exception:
            continue

        bbox_x.append(x / page_w)
        bbox_y.append(y / page_h)
        bbox_w.append(w / page_w)
        bbox_h.append(h / page_h)
        bbox_area_ratio.append((w * h) / page_area)

    for block in blocks:
        bt = str(block.get("block_type", "")).lower()
        bbox = block.get("bbox") or [0, 0, 0, 0]

        if bt == "table":
            table_blocks += 1
            try:
                _x, _y, w, h = [float(v) for v in bbox]
                table_area_ratio += (w * h) / page_area
            except Exception:
                pass

    text_mask_ratio = safe_ratio(float(meta.get("mask_text_nonzero", 0)), page_area)
    math_mask_ratio = safe_ratio(float(meta.get("mask_math_nonzero", 0)), page_area)

    total_lines = max(1, len(lines))
    total_blocks = max(1, len(blocks))

    return [
        float(len(blocks)),
        float(len(lines)),
        safe_ratio(text_lines, total_lines),
        safe_ratio(math_lines, total_lines),
        safe_ratio(table_blocks, total_blocks),
        float(table_area_ratio),
        float(text_mask_ratio),
        float(math_mask_ratio),
        _mean(bbox_x),
        _mean(bbox_y),
        _std(bbox_x),
        _std(bbox_y),
        _mean(bbox_w),
        _mean(bbox_h),
        _std(bbox_area_ratio),
    ]


def _pairwise_euclidean_distances(vectors: list[list[float]]) -> list[float]:
    if len(vectors) < 2:
        return []

    arr = np.asarray(vectors, dtype=np.float64)

    # Normalize columns so different feature scales do not dominate.
    col_std = np.std(arr, axis=0)
    col_std[col_std == 0] = 1.0
    arr = (arr - np.mean(arr, axis=0)) / col_std

    distances: list[float] = []

    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            distances.append(float(np.linalg.norm(arr[i] - arr[j])))

    return distances


def measure_mathematical_diversity(out_root: Path) -> dict[str, Any]:
    """
    Measure diversity from generated annotations only.

    This does not compare against any external dataset. It checks whether the
    generator's own output distribution has enough structural spread.
    """
    pairs = load_ann_gt_pairs(out_root)

    signatures: list[str] = []
    vectors: list[list[float]] = []

    line_counts: list[float] = []
    block_counts: list[float] = []
    text_mask_ratios: list[float] = []
    math_mask_ratios: list[float] = []
    table_area_ratios: list[float] = []

    block_type_counts = {
        "text": 0,
        "table": 0,
        "math": 0,
        "other": 0,
    }

    for _ann_path, ann, _gt_path, _gt in pairs:
        signatures.append(_layout_signature_for_page(ann))
        vectors.append(_page_feature_vector(ann))

        size = ann.get("size") or {}
        meta = ann.get("meta") or {}
        page_area = max(1, int(size.get("w", 1) or 1) * int(size.get("h", 1) or 1))

        lines = ann.get("lines", []) or []
        blocks = ann.get("blocks", []) or []

        line_counts.append(float(len(lines)))
        block_counts.append(float(len(blocks)))

        text_mask_ratios.append(safe_ratio(float(meta.get("mask_text_nonzero", 0)), page_area))
        math_mask_ratios.append(safe_ratio(float(meta.get("mask_math_nonzero", 0)), page_area))

        page_table_area = 0.0

        for block in blocks:
            bt = str(block.get("block_type", "")).lower()
            bbox = block.get("bbox") or [0, 0, 0, 0]

            if bt == "table":
                block_type_counts["table"] += 1
                try:
                    _x, _y, w, h = [float(v) for v in bbox]
                    page_table_area += (w * h) / page_area
                except Exception:
                    pass
            elif bt in {"text", "paragraph", "title", "caption"}:
                block_type_counts["text"] += 1
            elif bt in {"math", "latex", "equation"}:
                block_type_counts["math"] += 1
            else:
                block_type_counts["other"] += 1

        table_area_ratios.append(float(page_table_area))

    page_count = len(pairs)
    unique_signatures = len(set(signatures))
    unique_layout_signature_ratio = safe_ratio(unique_signatures, page_count)

    signature_counts = [signatures.count(sig) for sig in sorted(set(signatures))]
    layout_entropy = _entropy_from_counts(signature_counts)
    layout_entropy_normalized = _normalized_entropy_from_counts(signature_counts)

    block_type_entropy = _entropy_from_counts(list(block_type_counts.values()))
    block_type_entropy_normalized = _normalized_entropy_from_counts(list(block_type_counts.values()))

    distances = _pairwise_euclidean_distances(vectors)

    pairwise_distance_mean = _mean(distances)
    pairwise_distance_min = float(min(distances)) if distances else 0.0
    pairwise_distance_std = _std(distances)

    # Collapse risk should be high when signatures are repeated and distances are too low.
    uniqueness_component = unique_layout_signature_ratio
    entropy_component = layout_entropy_normalized
    distance_component = clamp01(pairwise_distance_mean / 2.0)

    mathematical_diversity_score = clamp01(
        0.35 * uniqueness_component
        + 0.25 * entropy_component
        + 0.20 * distance_component
        + 0.10 * clamp01(_std(line_counts) / 10.0)
        + 0.10 * clamp01(block_type_entropy_normalized)
    )

    collapse_score = clamp01(1.0 - mathematical_diversity_score)

    return {
        "mathematical_diversity_pages": page_count,
        "unique_layout_signatures": unique_signatures,
        "unique_layout_signature_ratio": unique_layout_signature_ratio,
        "layout_entropy": layout_entropy,
        "layout_entropy_normalized": layout_entropy_normalized,
        "block_type_entropy": block_type_entropy,
        "block_type_entropy_normalized": block_type_entropy_normalized,
        "line_count_mean": _mean(line_counts),
        "line_count_std": _std(line_counts),
        "block_count_mean": _mean(block_counts),
        "block_count_std": _std(block_counts),
        "text_mask_ratio_mean_mathdiv": _mean(text_mask_ratios),
        "text_mask_ratio_std_mathdiv": _std(text_mask_ratios),
        "math_mask_ratio_mean_mathdiv": _mean(math_mask_ratios),
        "math_mask_ratio_std_mathdiv": _std(math_mask_ratios),
        "table_area_ratio_mean_mathdiv": _mean(table_area_ratios),
        "table_area_ratio_std_mathdiv": _std(table_area_ratios),
        "pairwise_layout_distance_mean": pairwise_distance_mean,
        "pairwise_layout_distance_min": pairwise_distance_min,
        "pairwise_layout_distance_std": pairwise_distance_std,
        "collapse_score": collapse_score,
        "mathematical_diversity_score": mathematical_diversity_score,
    }



