# test_artifacts/real_generation_diagnostic_v3_class_based.py
from __future__ import annotations

import argparse
import json
import math
import shutil
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from docsynthfab.gui.web.simple_controls import collect_simple_overrides
from docsynthfab.gui.web.state import WebGuiState
from docsynthfab.orchestrator import RunOrchestrator, RunRequest


@dataclass(frozen=True)
class Scenario:
    name: str
    text_mix: float
    table_mix: float
    latex_mix: float = 0.0
    density_percent: float = 75.0
    whitespace_strategy: str = "balanced"
    spread_percent: float = 70.0
    block_gap_percent: float = 24.0
    placement_search_percent: float = 70.0
    line_gap_randomness_percent: float = 35.0
    expected_table: bool = False


@dataclass(frozen=True)
class DiagnosticRunConfig:
    root: Path
    art: Path
    page_counts: list[int]
    scenarios: list[Scenario]
    workers: int
    timeout_s: float
    volume: str


class DiagnosticVolume:
    PAGE_COUNTS: dict[str, list[int]] = {
        "small": [10, 25],
        "medium": [50, 100],
        "high": [200, 500],
    }

    DEFAULT = "small"

    @classmethod
    def choices(cls) -> list[str]:
        return sorted(cls.PAGE_COUNTS.keys())

    @classmethod
    def parse_page_counts(cls, raw: str, *, volume: str | None = None) -> list[int]:
        out: list[int] = []

        for part in str(raw or "").split(","):
            part = part.strip()
            if part:
                out.append(int(part))

        if out:
            return out

        volume = str(volume or cls.DEFAULT).strip().lower()
        return list(cls.PAGE_COUNTS.get(volume, cls.PAGE_COUNTS[cls.DEFAULT]))


class ScenarioRegistry:
    @classmethod
    def all(cls) -> list[Scenario]:
        return [
            Scenario(
                name="text_only_dense",
                text_mix=100,
                table_mix=0,
                density_percent=90,
                whitespace_strategy="compact",
                spread_percent=72,
                block_gap_percent=18,
                line_gap_randomness_percent=30,
                expected_table=False,
            ),
            Scenario(
                name="text_only_balanced",
                text_mix=100,
                table_mix=0,
                density_percent=72,
                whitespace_strategy="balanced",
                spread_percent=76,
                block_gap_percent=24,
                line_gap_randomness_percent=35,
                expected_table=False,
            ),
            Scenario(
                name="text_only_airy",
                text_mix=100,
                table_mix=0,
                density_percent=45,
                whitespace_strategy="airy",
                spread_percent=90,
                block_gap_percent=40,
                line_gap_randomness_percent=55,
                expected_table=False,
            ),
            Scenario(
                name="text_table_light",
                text_mix=85,
                table_mix=15,
                density_percent=70,
                whitespace_strategy="balanced",
                spread_percent=78,
                block_gap_percent=26,
                line_gap_randomness_percent=38,
                expected_table=True,
            ),
            Scenario(
                name="text_table_balanced",
                text_mix=70,
                table_mix=30,
                density_percent=75,
                whitespace_strategy="balanced",
                spread_percent=72,
                block_gap_percent=24,
                line_gap_randomness_percent=35,
                expected_table=True,
            ),
            Scenario(
                name="text_table_dense",
                text_mix=65,
                table_mix=35,
                density_percent=88,
                whitespace_strategy="compact",
                spread_percent=70,
                block_gap_percent=18,
                line_gap_randomness_percent=30,
                expected_table=True,
            ),
            Scenario(
                name="airy_text_table",
                text_mix=75,
                table_mix=25,
                density_percent=45,
                whitespace_strategy="airy",
                spread_percent=88,
                block_gap_percent=38,
                line_gap_randomness_percent=55,
                expected_table=True,
            ),
            Scenario(
                name="table_heavy",
                text_mix=35,
                table_mix=65,
                density_percent=70,
                whitespace_strategy="compact",
                spread_percent=68,
                block_gap_percent=20,
                line_gap_randomness_percent=32,
                expected_table=True,
            ),
            Scenario(
                name="table_heavy_dense",
                text_mix=25,
                table_mix=75,
                density_percent=88,
                whitespace_strategy="compact",
                spread_percent=66,
                block_gap_percent=16,
                line_gap_randomness_percent=28,
                expected_table=True,
            ),
            Scenario(
                name="table_heavy_airy",
                text_mix=40,
                table_mix=60,
                density_percent=50,
                whitespace_strategy="airy",
                spread_percent=88,
                block_gap_percent=40,
                line_gap_randomness_percent=55,
                expected_table=True,
            ),
            Scenario(
                name="sparse_report",
                text_mix=90,
                table_mix=10,
                density_percent=35,
                whitespace_strategy="airy",
                spread_percent=92,
                block_gap_percent=44,
                line_gap_randomness_percent=60,
                expected_table=True,
            ),
            Scenario(
                name="compact_report",
                text_mix=80,
                table_mix=20,
                density_percent=92,
                whitespace_strategy="compact",
                spread_percent=66,
                block_gap_percent=14,
                line_gap_randomness_percent=25,
                expected_table=True,
            ),
            Scenario(
                name="balanced_report",
                text_mix=75,
                table_mix=25,
                density_percent=68,
                whitespace_strategy="balanced",
                spread_percent=78,
                block_gap_percent=26,
                line_gap_randomness_percent=40,
                expected_table=True,
            ),
            Scenario(
                name="table_micro_cells",
                text_mix=45,
                table_mix=55,
                density_percent=82,
                whitespace_strategy="compact",
                spread_percent=70,
                block_gap_percent=18,
                line_gap_randomness_percent=30,
                expected_table=True,
            ),
            Scenario(
                name="layout_stress_mixed",
                text_mix=60,
                table_mix=40,
                density_percent=86,
                whitespace_strategy="balanced",
                spread_percent=82,
                block_gap_percent=18,
                placement_search_percent=90,
                line_gap_randomness_percent=50,
                expected_table=True,
            ),
        ]

    @classmethod
    def selected(cls, raw: str | None) -> list[Scenario]:
        scenarios = cls.all()

        if not raw:
            return scenarios

        wanted = {x.strip() for x in raw.split(",") if x.strip()}
        by_name = {s.name: s for s in scenarios}
        missing = sorted(wanted - set(by_name))

        if missing:
            raise SystemExit(f"Unknown scenarios: {missing}. Available: {sorted(by_name)}")

        return [by_name[name] for name in wanted]


class W:
    def __init__(self, value: Any = None):
        self.value = value


class WebStateFactory:
    @staticmethod
    def make_state(scenario: Scenario) -> WebGuiState:
        state = WebGuiState()

        state.dataset_goal_select = W("Quick OCR Dataset")
        state.dataset_character_select = W("Balanced")
        state.text_length_select = W("Balanced blocks")
        state.diversity_strength_select = W("Balanced diversity")
        state.document_template_select = W("Generic random document")

        state.content_mix_preset_select = W("Custom")
        state.text_mix_input = W(scenario.text_mix)
        state.table_mix_input = W(scenario.table_mix)
        state.latex_mix_input = W(scenario.latex_mix)

        state.content_source_mode_select = W("word_bank")
        state.text_min_words_input = W(18)
        state.text_max_words_input = W(32)
        state.sentence_min_input = W(2)
        state.sentence_max_input = W(4)

        state.table_min_rows_input = W(2)
        state.table_max_rows_input = W(5)
        state.table_min_cols_input = W(2)
        state.table_max_cols_input = W(4)

        state.density_percent_input = W(scenario.density_percent)
        state.layout_randomness_percent_input = W(75)
        state.negative_space_profile_select = W("Controlled")
        state.line_gap_tolerance_input = W(scenario.line_gap_randomness_percent)
        state.whitespace_strategy_select = W(scenario.whitespace_strategy)

        state.spread_percent_input = W(scenario.spread_percent)
        state.block_gap_percent_input = W(scenario.block_gap_percent)
        state.placement_search_percent_input = W(scenario.placement_search_percent)

        state.font_size_profile_select = W("Balanced")
        state.font_min_px_input = W(10)
        state.font_max_px_input = W(18)

        return state

    @staticmethod
    def make_overrides(scenario: Scenario) -> dict[str, Any]:
        state = WebStateFactory.make_state(scenario)
        overrides = collect_simple_overrides(state)

        overrides["augment.enable"] = True
        overrides["diversity_preset"] = "balanced_document_ai_diverse"

        OverrideValidator.validate(overrides)

        return overrides


class JsonUtils:
    @staticmethod
    def load_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8-sig"))


class MathUtils:
    @staticmethod
    def safe_ratio(num: float, den: float) -> float:
        if den <= 0:
            return 0.0
        return float(num) / float(den)

    @staticmethod
    def mean(values: list[float]) -> float:
        return float(sum(values) / len(values)) if values else 0.0

    @staticmethod
    def std(values: list[float]) -> float:
        if len(values) <= 1:
            return 0.0
        avg = MathUtils.mean(values)
        return float((sum((x - avg) ** 2 for x in values) / len(values)) ** 0.5)

    @staticmethod
    def entropy_from_counts(counts: Iterable[int]) -> float:
        values = [float(x) for x in counts if int(x) > 0]
        total = sum(values)
        if total <= 0:
            return 0.0
        return float(-sum((x / total) * math.log2(x / total) for x in values))

    @staticmethod
    def normalized_entropy(counts: Iterable[int]) -> float:
        values = [int(x) for x in counts if int(x) > 0]
        if len(values) <= 1:
            return 0.0
        return MathUtils.safe_ratio(MathUtils.entropy_from_counts(values), math.log2(len(values)))


class GeometryUtils:
    @staticmethod
    def bbox_rect(bbox: Any) -> tuple[float, float, float, float] | None:
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            return None

        try:
            x, y, w, h = [float(v) for v in bbox]
        except Exception:
            return None

        if w <= 0 or h <= 0:
            return None

        return x, y, x + w, y + h

    @staticmethod
    def bbox_inside_page(bbox: Any, page_w: int, page_h: int) -> bool:
        rect = GeometryUtils.bbox_rect(bbox)
        if rect is None:
            return False

        x0, y0, x1, y1 = rect
        return x0 >= 0 and y0 >= 0 and x1 <= page_w and y1 <= page_h

    @staticmethod
    def overlap_ratio_min_area(a: Any, b: Any) -> float:
        ra = GeometryUtils.bbox_rect(a)
        rb = GeometryUtils.bbox_rect(b)

        if ra is None or rb is None:
            return 0.0

        ax0, ay0, ax1, ay1 = ra
        bx0, by0, bx1, by1 = rb

        ix0 = max(ax0, bx0)
        iy0 = max(ay0, by0)
        ix1 = min(ax1, bx1)
        iy1 = min(ay1, by1)

        if ix1 <= ix0 or iy1 <= iy0:
            return 0.0

        inter = (ix1 - ix0) * (iy1 - iy0)
        area_a = max(1.0, (ax1 - ax0) * (ay1 - ay0))
        area_b = max(1.0, (bx1 - bx0) * (by1 - by0))

        return MathUtils.safe_ratio(inter, min(area_a, area_b))

    @staticmethod
    def center_grid_bin(bbox: Any, page_w: int, page_h: int, grid: int = 4) -> str | None:
        rect = GeometryUtils.bbox_rect(bbox)
        if rect is None:
            return None

        x0, y0, x1, y1 = rect
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0

        gx = max(0, min(grid - 1, int((cx / max(1, page_w)) * grid)))
        gy = max(0, min(grid - 1, int((cy / max(1, page_h)) * grid)))

        return f"{gx},{gy}"


class OverrideValidator:
    @staticmethod
    def validate(overrides: dict[str, Any]) -> None:
        policy = overrides.get("content.word_bank_policy", {})
        line_gap = overrides.get("layout.line_gap", {})
        words_cfg = overrides.get("content.words", {})

        assert overrides.get("content.source_mode") == "content_bank", overrides
        assert overrides.get("content.text_mode") == "words", overrides
        assert words_cfg.get("min_words") == 18, words_cfg
        assert words_cfg.get("max_words") == 32, words_cfg

        assert policy.get("enable") is True, policy
        assert policy.get("primary") == "alphabet", policy
        assert policy.get("mix_strategy") == "dominant_sentence", policy
        assert policy.get("group_multilingual") is False, policy
        assert int(policy.get("min_alphabets_per_group", 0)) == 1, policy

        assert policy.get("sentence_language_mode") == "dominant", policy
        assert 0.0 <= float(policy.get("sentence_language_switch_prob", 0.0)) <= 0.10, policy
        assert 0.05 <= float(policy.get("table_cell_sentence_prob", 0.0)) <= 0.30, policy
        assert int(policy.get("table_cell_sentence_min_words", 0)) >= 1, policy
        assert int(policy.get("table_cell_sentence_max_words", 0)) >= int(
            policy.get("table_cell_sentence_min_words", 0)
        ), policy

        assert line_gap.get("distribution") in {
            "gaussian",
            "uniform",
            "lognormal",
            "exponential",
        }, line_gap


class NegativeSpaceAnalyzer:
    @staticmethod
    def limits(scenario: Scenario) -> dict[str, float]:
        strategy = scenario.whitespace_strategy.strip().lower()
        density = float(scenario.density_percent)

        if strategy == "airy":
            min_negative = 0.50
            max_negative = 0.94
            max_largest_empty_region = 0.72
        elif strategy in {"compact", "packed"}:
            min_negative = 0.35
            max_negative = 0.88
            max_largest_empty_region = 0.55
        else:
            min_negative = 0.42
            max_negative = 0.91
            max_largest_empty_region = 0.62

        if density >= 85:
            max_negative -= 0.06
            max_largest_empty_region -= 0.08
        elif density <= 50:
            max_negative += 0.03
            max_largest_empty_region += 0.08

        if scenario.expected_table:
            max_negative -= 0.03

        return {
            "min_negative_space_ratio": max(0.20, min_negative),
            "max_negative_space_ratio": min(0.97, max_negative),
            "max_largest_empty_region_ratio": min(0.90, max_largest_empty_region),
        }

    @staticmethod
    def approximate(
        blocks: list[dict[str, Any]],
        *,
        page_w: int,
        page_h: int,
        grid: int = 48,
    ) -> dict[str, float]:
        if page_w <= 0 or page_h <= 0:
            return {
                "block_occupancy_ratio": 0.0,
                "negative_space_ratio": 1.0,
                "largest_empty_region_ratio": 1.0,
            }

        occupied = [[False for _ in range(grid)] for _ in range(grid)]

        for block in blocks:
            rect = GeometryUtils.bbox_rect(block.get("bbox"))
            if rect is None:
                continue

            x0, y0, x1, y1 = rect

            gx0 = max(0, min(grid - 1, int((x0 / page_w) * grid)))
            gy0 = max(0, min(grid - 1, int((y0 / page_h) * grid)))
            gx1 = max(0, min(grid - 1, int(math.ceil((x1 / page_w) * grid)) - 1))
            gy1 = max(0, min(grid - 1, int(math.ceil((y1 / page_h) * grid)) - 1))

            for gy in range(gy0, gy1 + 1):
                for gx in range(gx0, gx1 + 1):
                    occupied[gy][gx] = True

        total_cells = grid * grid
        occupied_count = sum(1 for row in occupied for cell in row if cell)
        empty_count = total_cells - occupied_count

        seen = [[False for _ in range(grid)] for _ in range(grid)]
        largest_empty = 0

        for sy in range(grid):
            for sx in range(grid):
                if occupied[sy][sx] or seen[sy][sx]:
                    continue

                stack = [(sx, sy)]
                seen[sy][sx] = True
                region = 0

                while stack:
                    x, y = stack.pop()
                    region += 1

                    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                        if nx < 0 or ny < 0 or nx >= grid or ny >= grid:
                            continue
                        if seen[ny][nx] or occupied[ny][nx]:
                            continue
                        seen[ny][nx] = True
                        stack.append((nx, ny))

                largest_empty = max(largest_empty, region)

        return {
            "block_occupancy_ratio": MathUtils.safe_ratio(occupied_count, total_cells),
            "negative_space_ratio": MathUtils.safe_ratio(empty_count, total_cells),
            "largest_empty_region_ratio": MathUtils.safe_ratio(largest_empty, total_cells),
        }


class QualityAnalyzer:
    def __init__(self, *, expected_pages: int, scenario: Scenario):
        self.expected_pages = int(expected_pages)
        self.scenario = scenario

    def collect(self, out_root: Path) -> dict[str, Any]:
        image_dir = out_root / "images"
        ann_dir = out_root / "ann"
        gt_dir = out_root / "gt"
        mask_dir = out_root / "masks"

        image_paths = sorted(image_dir.glob("*.png")) if image_dir.exists() else []
        ann_paths = sorted(ann_dir.glob("*.json")) if ann_dir.exists() else []
        gt_paths = sorted(gt_dir.glob("*.json")) if gt_dir.exists() else []
        mask_paths = sorted(mask_dir.glob("*.png")) if mask_dir.exists() else []

        image_stems = {p.stem for p in image_paths}
        ann_stems = {p.stem for p in ann_paths}
        gt_stems = {p.stem for p in gt_paths}

        json_errors: list[dict[str, Any]] = []
        empty_json: list[str] = []
        invalid_bbox: list[dict[str, Any]] = []
        block_overlap: list[dict[str, Any]] = []
        line_overlap: list[dict[str, Any]] = []
        blank_pages: list[dict[str, Any]] = []
        low_content_pages: list[dict[str, Any]] = []
        negative_space_outliers: list[dict[str, Any]] = []

        density_counts = Counter()
        script_counts = Counter()
        noise_counts = Counter()
        layout_counts = Counter()
        scale_counts = Counter()
        page_family_counts = Counter()
        position_bins = Counter()

        line_count_total = 0
        block_count_total = 0
        text_line_total = 0
        math_line_total = 0
        table_block_total = 0
        pages_with_table = 0
        pages_with_text = 0
        text_table_mixed_pages = 0

        text_mask_ratios: list[float] = []
        math_mask_ratios: list[float] = []
        block_occupancy_ratios: list[float] = []
        negative_space_ratios: list[float] = []
        largest_empty_region_ratios: list[float] = []
        sample_texts: list[str] = []

        min_content_ratio = 0.0015
        min_content_pixels = 64
        negative_limits = NegativeSpaceAnalyzer.limits(self.scenario)

        for ann_path in ann_paths:
            try:
                ann = JsonUtils.load_json(ann_path)
            except Exception as exc:
                json_errors.append({"file": str(ann_path), "error": repr(exc)})
                continue

            if not ann:
                empty_json.append(str(ann_path))
                continue

            size = ann.get("size") or {}
            page_w = int(size.get("w", 0) or 0)
            page_h = int(size.get("h", 0) or 0)
            page_area = max(1, page_w * page_h)

            meta = ann.get("meta") or {}
            density_counts[str(meta.get("density_level", "unknown"))] += 1
            noise_counts[str(meta.get("noise_level", "unknown"))] += 1
            layout_counts[str(meta.get("layout_type", "unknown"))] += 1
            scale_counts[str(meta.get("scale_profile", "unknown"))] += 1
            page_family_counts[str(meta.get("page_family", "unknown"))] += 1

            text_pixels = int(meta.get("mask_text_nonzero", 0) or 0)
            math_pixels = int(meta.get("mask_math_nonzero", 0) or 0)
            content_pixels = text_pixels + math_pixels
            content_ratio = MathUtils.safe_ratio(content_pixels, page_area)

            text_mask_ratios.append(MathUtils.safe_ratio(text_pixels, page_area))
            math_mask_ratios.append(MathUtils.safe_ratio(math_pixels, page_area))

            if content_pixels <= 0:
                blank_pages.append({
                    "file": ann_path.name,
                    "content_pixels": content_pixels,
                    "content_ratio": content_ratio,
                })
            elif content_pixels < min_content_pixels or content_ratio < min_content_ratio:
                low_content_pages.append({
                    "file": ann_path.name,
                    "content_pixels": content_pixels,
                    "content_ratio": content_ratio,
                })

            lines = ann.get("lines") or []
            blocks = ann.get("blocks") or []

            line_count_total += len(lines)
            block_count_total += len(blocks)

            negative = NegativeSpaceAnalyzer.approximate(blocks, page_w=page_w, page_h=page_h)
            block_occupancy = float(negative["block_occupancy_ratio"])
            negative_space = float(negative["negative_space_ratio"])
            largest_empty_region = float(negative["largest_empty_region_ratio"])

            block_occupancy_ratios.append(block_occupancy)
            negative_space_ratios.append(negative_space)
            largest_empty_region_ratios.append(largest_empty_region)

            if (
                negative_space < negative_limits["min_negative_space_ratio"]
                or negative_space > negative_limits["max_negative_space_ratio"]
                or largest_empty_region > negative_limits["max_largest_empty_region_ratio"]
            ):
                negative_space_outliers.append({
                    "file": ann_path.name,
                    "negative_space_ratio": negative_space,
                    "block_occupancy_ratio": block_occupancy,
                    "largest_empty_region_ratio": largest_empty_region,
                    "limits": negative_limits,
                })

            page_text_lines = 0
            page_table_blocks = 0

            for index, block in enumerate(blocks):
                bbox = block.get("bbox")

                if not GeometryUtils.bbox_inside_page(bbox, page_w, page_h):
                    invalid_bbox.append({
                        "file": ann_path.name,
                        "kind": "block",
                        "index": index,
                        "bbox": bbox,
                    })

                bin_id = GeometryUtils.center_grid_bin(bbox, page_w, page_h)
                if bin_id is not None:
                    position_bins[bin_id] += 1

                bt = str(block.get("block_type", "")).lower()
                if bt == "table":
                    page_table_blocks += 1
                    table_block_total += 1

            for i in range(len(blocks)):
                for j in range(i + 1, len(blocks)):
                    ratio = GeometryUtils.overlap_ratio_min_area(
                        blocks[i].get("bbox"),
                        blocks[j].get("bbox"),
                    )
                    if ratio > 0.35:
                        block_overlap.append({
                            "file": ann_path.name,
                            "i": i,
                            "j": j,
                            "ratio": ratio,
                            "type_i": blocks[i].get("block_type"),
                            "type_j": blocks[j].get("block_type"),
                        })

            for index, line in enumerate(lines):
                bbox = line.get("bbox")

                if not GeometryUtils.bbox_inside_page(bbox, page_w, page_h):
                    invalid_bbox.append({
                        "file": ann_path.name,
                        "kind": "line",
                        "index": index,
                        "bbox": bbox,
                    })

                lt = str(line.get("line_type", "text")).lower()
                is_math = lt in {"math", "latex", "equation"} or bool(
                    line.get("gt_latex") or line.get("latex")
                )

                if is_math:
                    math_line_total += 1
                else:
                    text_line_total += 1
                    page_text_lines += 1

                if line.get("gt_script"):
                    script_counts[str(line.get("gt_script"))] += 1

                text = (
                    line.get("gt_text")
                    or line.get("text")
                    or line.get("gt_latex")
                    or line.get("latex")
                    or ""
                )
                text = str(text).strip()

                if text and len(sample_texts) < 20:
                    sample_texts.append(text)

            for i in range(len(lines)):
                for j in range(i + 1, len(lines)):
                    ratio = GeometryUtils.overlap_ratio_min_area(
                        lines[i].get("bbox"),
                        lines[j].get("bbox"),
                    )
                    if ratio > 0.60:
                        line_overlap.append({
                            "file": ann_path.name,
                            "i": i,
                            "j": j,
                            "ratio": ratio,
                            "type_i": lines[i].get("line_type"),
                            "type_j": lines[j].get("line_type"),
                        })

            if page_table_blocks > 0:
                pages_with_table += 1

            if page_text_lines > 0:
                pages_with_text += 1

            if page_table_blocks > 0 and page_text_lines > 0:
                text_table_mixed_pages += 1

        position_grid_cells = 16
        position_grid_coverage_ratio = MathUtils.safe_ratio(len(position_bins), position_grid_cells)
        position_entropy_normalized = MathUtils.normalized_entropy(position_bins.values())

        table_presence_ratio = MathUtils.safe_ratio(pages_with_table, len(ann_paths))
        text_table_mixed_page_ratio = MathUtils.safe_ratio(text_table_mixed_pages, len(ann_paths))

        text_mask_ratio_min = min(text_mask_ratios) if text_mask_ratios else 0.0

        quality = {
            "blank_page_count": len(blank_pages),
            "low_content_page_count": len(low_content_pages),
            "negative_space_outlier_count": len(negative_space_outliers),
            "negative_space_limits": negative_limits,
            "block_occupancy_ratio_mean": MathUtils.mean(block_occupancy_ratios),
            "block_occupancy_ratio_std": MathUtils.std(block_occupancy_ratios),
            "negative_space_ratio_min": min(negative_space_ratios) if negative_space_ratios else 0.0,
            "negative_space_ratio_max": max(negative_space_ratios) if negative_space_ratios else 0.0,
            "negative_space_ratio_mean": MathUtils.mean(negative_space_ratios),
            "negative_space_ratio_std": MathUtils.std(negative_space_ratios),
            "largest_empty_region_ratio_mean": MathUtils.mean(largest_empty_region_ratios),
            "largest_empty_region_ratio_max": max(largest_empty_region_ratios) if largest_empty_region_ratios else 0.0,
            "invalid_bbox_count": len(invalid_bbox),
            "block_overlap_violation_count": len(block_overlap),
            "line_overlap_violation_count": len(line_overlap),
            "position_grid_coverage_ratio": position_grid_coverage_ratio,
            "position_entropy_normalized": position_entropy_normalized,
            "text_mask_ratio_min": text_mask_ratio_min,
            "text_mask_ratio_mean": MathUtils.mean(text_mask_ratios),
            "math_mask_ratio_mean": MathUtils.mean(math_mask_ratios),
            "table_presence_ratio": table_presence_ratio,
            "text_table_mixed_page_ratio": text_table_mixed_page_ratio,
            "pages_with_table": pages_with_table,
            "pages_with_text": pages_with_text,
        }

        failures: list[str] = []

        def fail_if(condition: bool, message: str) -> None:
            if condition:
                failures.append(message)

        fail_if(len(image_paths) != self.expected_pages, f"image count mismatch: {len(image_paths)} != {self.expected_pages}")
        fail_if(len(ann_paths) != self.expected_pages, f"ann count mismatch: {len(ann_paths)} != {self.expected_pages}")
        fail_if(len(gt_paths) != self.expected_pages, f"gt count mismatch: {len(gt_paths)} != {self.expected_pages}")
        fail_if(bool(image_stems - ann_stems), f"images without ann: {sorted(image_stems - ann_stems)[:10]}")
        fail_if(bool(image_stems - gt_stems), f"images without gt: {sorted(image_stems - gt_stems)[:10]}")
        fail_if(bool(json_errors), f"json errors: {len(json_errors)}")
        fail_if(bool(empty_json), f"empty json files: {len(empty_json)}")
        fail_if(bool(blank_pages), f"blank pages: {len(blank_pages)}")
        fail_if(bool(low_content_pages), f"low content pages: {len(low_content_pages)}")
        fail_if(bool(negative_space_outliers), f"negative space outliers: {len(negative_space_outliers)}")
        fail_if(bool(invalid_bbox), f"invalid bboxes: {len(invalid_bbox)}")
        fail_if(bool(block_overlap), f"block overlap violations: {len(block_overlap)}")

        line_overlap_limit = max(2, int(0.002 * max(1, line_count_total)))
        fail_if(len(line_overlap) > line_overlap_limit, f"line overlap violations: {len(line_overlap)}")

        min_position_coverage = 0.35
        if self.expected_pages >= 100:
            min_position_coverage = 0.45
        if self.expected_pages >= 200:
            min_position_coverage = 0.55
        if self.expected_pages >= 500:
            min_position_coverage = 0.65

        fail_if(
            position_grid_coverage_ratio < min_position_coverage,
            f"position grid coverage too low: {position_grid_coverage_ratio:.3f} < {min_position_coverage:.3f}",
        )

        if self.scenario.expected_table:
            min_table_presence = max(0.10, min(0.45, self.scenario.table_mix / 100.0 * 0.55))

            fail_if(
                table_presence_ratio < min_table_presence,
                f"table presence too low: {table_presence_ratio:.3f} < {min_table_presence:.3f}",
            )

            fail_if(
                text_table_mixed_page_ratio < min(0.35, min_table_presence),
                f"text-table mixed page ratio too low: {text_table_mixed_page_ratio:.3f}",
            )
        else:
            fail_if(table_block_total != 0, f"text-only scenario produced table blocks: {table_block_total}")

        quality_score = 1.0
        quality_score -= min(0.35, 0.05 * len(failures))
        quality_score -= min(0.20, MathUtils.safe_ratio(len(block_overlap), max(1, len(ann_paths))) * 0.20)
        quality_score -= min(0.15, MathUtils.safe_ratio(len(low_content_pages) + len(blank_pages), max(1, len(ann_paths))) * 0.50)
        quality_score -= min(0.15, MathUtils.safe_ratio(len(negative_space_outliers), max(1, len(ann_paths))) * 0.40)
        quality_score += min(0.10, position_entropy_normalized * 0.10)
        quality_score = max(0.0, min(1.0, quality_score))

        quality["quality_score"] = quality_score

        return {
            "ok": len(failures) == 0,
            "failures": failures,
            "counts": {
                "images": len(image_paths),
                "ann": len(ann_paths),
                "gt": len(gt_paths),
                "masks": len(mask_paths),
                "json_errors": len(json_errors),
                "empty_json": len(empty_json),
                "lines_total": line_count_total,
                "blocks_total": block_count_total,
                "text_lines_total": text_line_total,
                "math_lines_total": math_line_total,
                "table_blocks_total": table_block_total,
            },
            "quality": quality,
            "samples": {
                "blank_pages": blank_pages[:20],
                "low_content_pages": low_content_pages[:20],
                "negative_space_outliers": negative_space_outliers[:20],
                "invalid_bbox": invalid_bbox[:20],
                "block_overlap": block_overlap[:20],
                "line_overlap": line_overlap[:20],
                "sample_texts": sample_texts,
            },
            "distributions": {
                "density_counts": dict(density_counts),
                "script_counts": dict(script_counts),
                "noise_counts": dict(noise_counts),
                "layout_counts": dict(layout_counts),
                "scale_counts": dict(scale_counts),
                "page_family_counts": dict(page_family_counts),
                "position_bins": dict(position_bins),
            },
        }


class BatchRunner:
    TERMINAL_STATES = {"done", "completed", "failed", "error", "cancelled"}

    def __init__(self, orch: RunOrchestrator):
        self.orch = orch

    def run_one(
        self,
        *,
        root: Path,
        art: Path,
        pages: int,
        scenario: Scenario,
        workers: int,
        timeout_s: float,
    ) -> dict[str, Any]:
        out_root = art / "batch_pages_v2" / scenario.name / f"pages_{pages:04d}"

        if out_root.exists():
            shutil.rmtree(out_root)

        seed = 12345 + pages + abs(hash(scenario.name)) % 100_000

        overrides = WebStateFactory.make_overrides(scenario)

        req = RunRequest(
            config_path=str(root / "configs" / "default.yaml"),
            out_root=str(out_root),
            pages=pages,
            workers=workers,
            seed=seed,
            smoke_test=False,
            export_targets=["native"],
            overrides=overrides,
            raw_yaml_override_text="",
        )

        effective = self.orch.build_effective_config_dict(req)

        print("")
        print("=" * 80)
        print(f"START scenario={scenario.name} pages={pages} out_root={out_root}")
        print("=" * 80)

        print(json.dumps({
            "scenario": asdict(scenario),
            "pages": pages,
            "seed": seed,
            "workers": workers,
            "content_block_mix": effective.get("content", {}).get("block_mix"),
            "density_dist": effective.get("dist", {}).get("density_dist"),
            "line_gap": effective.get("layout", {}).get("line_gap"),
            "occupancy": effective.get("layout", {}).get("occupancy"),
            "font_size": effective.get("render", {}).get("text", {}).get("font_size"),
            "scripts_dist": effective.get("render", {}).get("text", {}).get("scripts_dist"),
        }, ensure_ascii=False, indent=2))

        started = time.time()
        run_id = self.orch.start(req)

        deadline = time.time() + timeout_s
        status = None
        tick = 0

        while time.time() < deadline:
            status = self.orch.get_status(run_id)
            obj = status.to_dict()

            if tick % 10 == 0 or str(obj.get("state")) in self.TERMINAL_STATES:
                print(json.dumps({
                    "scenario": scenario.name,
                    "pages": pages,
                    "tick": tick,
                    "run_id": obj.get("run_id"),
                    "state": obj.get("state"),
                    "pid": obj.get("pid"),
                    "return_code": obj.get("return_code"),
                    "out_root": obj.get("out_root"),
                }, ensure_ascii=False))

            if str(obj.get("state")) in self.TERMINAL_STATES:
                break

            time.sleep(0.5)
            tick += 1

        elapsed = time.time() - started

        summary = self.orch.get_summary(run_id)
        summary_obj = summary.to_dict() if hasattr(summary, "to_dict") else str(summary)

        output_report = QualityAnalyzer(
            expected_pages=pages,
            scenario=scenario,
        ).collect(out_root)

        result = {
            "scenario": asdict(scenario),
            "pages_requested": pages,
            "seed": seed,
            "workers": workers,
            "run_id": run_id,
            "elapsed_seconds": elapsed,
            "out_root": str(out_root),
            "final_status": status.to_dict() if status is not None else None,
            "summary": summary_obj,
            "output_report": output_report,
            "effective_selected": {
                "content_block_mix": effective.get("content", {}).get("block_mix"),
                "density_dist": effective.get("dist", {}).get("density_dist"),
                "line_gap": effective.get("layout", {}).get("line_gap"),
                "occupancy": effective.get("layout", {}).get("occupancy"),
                "font_size": effective.get("render", {}).get("text", {}).get("font_size"),
                "scripts_dist": effective.get("render", {}).get("text", {}).get("scripts_dist"),
                "line_style_dist": effective.get("render", {}).get("text", {}).get("line_style_dist"),
            },
        }

        print("")
        print(f"END scenario={scenario.name} pages={pages}")
        print(json.dumps({
            "scenario": scenario.name,
            "pages": pages,
            "state": result["final_status"].get("state") if result["final_status"] else None,
            "return_code": result["final_status"].get("return_code") if result["final_status"] else None,
            "elapsed_seconds": round(elapsed, 2),
            "counts": output_report["counts"],
            "quality": output_report["quality"],
            "ok": output_report["ok"],
            "failures": output_report["failures"],
        }, ensure_ascii=False, indent=2))

        return result


class AggregateReportWriter:
    @staticmethod
    def write(
        batch_root: Path,
        page_counts: list[int],
        results: list[dict[str, Any]],
        *,
        volume: str,
    ) -> None:
        aggregate = {
            "volume": volume,
            "page_counts": page_counts,
            "created_at_unix": time.time(),
            "batch_root": str(batch_root),
            "results": results,
        }

        aggregate_json = batch_root / "batch_generation_quality_report.json"
        aggregate_md = batch_root / "batch_generation_quality_report.md"

        aggregate_json.write_text(
            json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        lines: list[str] = []
        lines.append("# Batch Generation Quality Report")
        lines.append("")
        lines.append(f"- Batch root: `{batch_root}`")
        lines.append(f"- Volume: `{volume}`")
        lines.append(f"- Page counts: `{page_counts}`")
        lines.append("")
        lines.append(
            "| Scenario | Pages | State | Images | ANN | GT | Blank | Low content | Neg out | Neg mean | Largest empty | Invalid bbox | Block overlap | Position coverage | Table pages | Mixed pages | Score | OK |"
        )
        lines.append(
            "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
        )

        for r in results:
            status = r.get("final_status") or {}
            out = r.get("output_report") or {}
            counts = out.get("counts") or {}
            quality = out.get("quality") or {}
            scenario = (r.get("scenario") or {}).get("name")

            lines.append(
                "| {scenario} | {pages} | {state} | {images} | {ann} | {gt} | {blank} | {low} | {neg_out} | {neg_mean:.3f} | {largest_empty:.3f} | {invalid} | {bover} | {pos:.3f} | {table_pages} | {mixed_pages:.3f} | {score:.3f} | {ok} |".format(
                    scenario=scenario,
                    pages=r.get("pages_requested"),
                    state=status.get("state"),
                    images=counts.get("images", 0),
                    ann=counts.get("ann", 0),
                    gt=counts.get("gt", 0),
                    blank=quality.get("blank_page_count", 0),
                    low=quality.get("low_content_page_count", 0),
                    neg_out=quality.get("negative_space_outlier_count", 0),
                    neg_mean=float(quality.get("negative_space_ratio_mean", 0.0) or 0.0),
                    largest_empty=float(quality.get("largest_empty_region_ratio_max", 0.0) or 0.0),
                    invalid=quality.get("invalid_bbox_count", 0),
                    bover=quality.get("block_overlap_violation_count", 0),
                    pos=float(quality.get("position_grid_coverage_ratio", 0.0) or 0.0),
                    table_pages=quality.get("pages_with_table", 0),
                    mixed_pages=float(quality.get("text_table_mixed_page_ratio", 0.0) or 0.0),
                    score=float(quality.get("quality_score", 0.0) or 0.0),
                    ok=out.get("ok"),
                )
            )

        lines.append("")
        lines.append("## Failures")
        lines.append("")

        any_failure = False

        for r in results:
            out = r.get("output_report") or {}
            failures = out.get("failures") or []

            if not failures:
                continue

            any_failure = True
            scenario = (r.get("scenario") or {}).get("name")
            lines.append(f"### {scenario} / pages {r.get('pages_requested')}")

            for failure in failures:
                lines.append(f"- {failure}")

            samples = out.get("samples") or {}

            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(samples, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

        if not any_failure:
            lines.append("No quality gate failures.")
            lines.append("")

        aggregate_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

        print(f"Wrote: {aggregate_json}")
        print(f"Wrote: {aggregate_md}")


class DiagnosticCLI:
    @staticmethod
    def parse_args() -> DiagnosticRunConfig:
        parser = argparse.ArgumentParser()

        parser.add_argument("--root", default=".", help="Project root.")
        parser.add_argument("--art", default=r"D:\ai1_gen_tes4", help="Artifact/output root.")
        parser.add_argument(
            "--volume",
            default=DiagnosticVolume.DEFAULT,
            choices=DiagnosticVolume.choices(),
            help="Test volume preset: small, medium, high.",
        )
        parser.add_argument(
            "--page-counts",
            default="",
            help="Comma-separated page counts. Overrides --volume when provided.",
        )
        parser.add_argument("--scenarios", default="", help="Comma-separated scenario names. Empty means all.")
        parser.add_argument("--workers", type=int, default=1)
        parser.add_argument("--timeout-s", type=float, default=7200.0)

        args = parser.parse_args()

        root = Path(args.root).resolve()
        art = Path(args.art)
        page_counts = DiagnosticVolume.parse_page_counts(args.page_counts, volume=args.volume)
        scenarios = ScenarioRegistry.selected(args.scenarios)

        return DiagnosticRunConfig(
            root=root,
            art=art,
            page_counts=page_counts,
            scenarios=scenarios,
            workers=int(args.workers),
            timeout_s=float(args.timeout_s),
            volume=str(args.volume),
        )

    @staticmethod
    def main() -> None:
        cfg = DiagnosticCLI.parse_args()

        if not (cfg.root / "configs" / "default.yaml").exists():
            raise SystemExit(f"Could not find configs/default.yaml under root={cfg.root}")

        batch_root = cfg.art / "batch_pages_v2"
        batch_root.mkdir(parents=True, exist_ok=True)

        orch = RunOrchestrator()
        runner = BatchRunner(orch)

        all_results: list[dict[str, Any]] = []

        for scenario in cfg.scenarios:
            for pages in cfg.page_counts:
                result = runner.run_one(
                    root=cfg.root,
                    art=cfg.art,
                    pages=pages,
                    scenario=scenario,
                    workers=cfg.workers,
                    timeout_s=cfg.timeout_s,
                )

                all_results.append(result)

                report_path = batch_root / scenario.name / f"report_pages_{pages:04d}.json"
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8",
                )

        AggregateReportWriter.write(
            batch_root,
            cfg.page_counts,
            all_results,
            volume=cfg.volume,
        )

        bad = [
            r for r in all_results
            if not ((r.get("output_report") or {}).get("ok"))
            or (r.get("final_status") or {}).get("state") not in {"done", "completed"}
        ]

        if bad:
            print("Some runs failed quality gates:")
            print(json.dumps([
                {
                    "scenario": (r.get("scenario") or {}).get("name"),
                    "pages": r.get("pages_requested"),
                    "state": (r.get("final_status") or {}).get("state"),
                    "failures": (r.get("output_report") or {}).get("failures"),
                }
                for r in bad
            ], ensure_ascii=False, indent=2))
            raise SystemExit(1)

        print("OK: all batch runs completed and passed quality gates.")


if __name__ == "__main__":
    DiagnosticCLI.main()
