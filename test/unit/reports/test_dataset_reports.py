from __future__ import annotations

import csv
import json
from pathlib import Path

from docsynthfab.reports.dataset_reports import (
    LABEL_SCHEMA_VERSION,
    build_dataset_card,
    build_diversity_summary,
    build_label_schema,
    collect_feature_rows,
    diversity_report_markdown,
    extract_feature_row,
    label_schema_markdown,
    write_dataset_reports,
    write_diversity_summary_csv,
    write_features,
    write_run_manifest,
)


def _sample_ann(page_id: str = "000001") -> dict:
    return {
        "version": "docsynthfab-ds-v0.1",
        "page_id": page_id,
        "size": {
            "w": 200,
            "h": 100,
            "dpi": 300,
            "page_size_name": "test",
            "page_width_in": 2.0,
            "page_height_in": 1.0,
            "orientation": "landscape",
        },
        "meta": {
            "layout_type": "single_col",
            "density_level": "normal",
            "noise_level": "clean",
            "scale_profile": "dpi300",
            "page_family": "report",
            "has_table": True,
            "has_equation": True,
            "has_equation_layout": True,
            "has_figure": False,
            "mask_text_nonzero": 1000,
            "mask_math_nonzero": 250,
            "math_line_count": 1,
            "table_block_count": 1,
            "equation_block_count": 1,
            "figure_block_count": 0,
            "rotation_deg": 0.0,
            "perspective": False,
            "book_mode": False,
            "_fallback": False,
            "aug_trace": [{"op": "photometric"}, {"op": "quick_quality_gate"}],
        },
        "gt_page_text": "Hello world\nx^2+y^2=z^2",
        "lines": [
            {
                "line_id": 0,
                "block_id": 0,
                "line_type": "text",
                "global_line_order": 0,
                "bbox": [10, 10, 80, 20],
                "gt_text": "Hello world",
                "gt_script": "latin",
            },
            {
                "line_id": 1,
                "block_id": 1,
                "line_type": "math",
                "global_line_order": 1,
                "bbox": [20, 40, 100, 20],
                "gt_latex": r"x^2+y^2=z^2",
                "gt_script": "symbols",
            },
        ],
        "blocks": [
            {
                "block_id": 0,
                "block_type": "table",
                "bbox": [5, 5, 100, 50],
            },
            {
                "block_id": 1,
                "block_type": "equation",
                "bbox": [20, 40, 100, 20],
            },
        ],
        "gt_stats": {},
    }


def test_build_label_schema_contains_expected_classes():
    schema = build_label_schema()

    assert schema["schema_version"] == LABEL_SCHEMA_VERSION
    assert schema["task_family"] == "document_ai"

    names = {c["name"] for c in schema["classes"]}

    assert "background" in names
    assert "plain_text" in names
    assert "table_region" in names
    assert "math_latex" in names
    assert "figure" in names

    assert schema["mask_channels"]["0"] == "background"
    assert schema["mask_channels"]["1"] == "plain_text"


def test_label_schema_markdown_contains_table_and_usage():
    md = label_schema_markdown(build_label_schema())

    assert "# Label Schema" in md
    assert "| ID | Name | Semantic type | OCR target | Mask channel | Recommended tasks |" in md
    assert "`plain_text`" in md
    assert "`math_latex`" in md
    assert "## Usage" in md


def test_extract_feature_row_reads_annotation_metadata():
    row = extract_feature_row(_sample_ann())

    assert row["page_id"] == "000001"
    assert row["layout_type"] == "single_col"
    assert row["density_level"] == "normal"
    assert row["has_table"] == 1
    assert row["has_equation"] == 1
    assert row["has_figure"] == 0
    assert row["line_count"] == 2
    assert row["block_count"] == 2
    assert row["math_line_count"] == 1
    assert row["table_block_count"] == 1
    assert row["equation_block_count"] == 1
    assert row["text_mask_ratio"] == 1000 / 20000
    assert row["math_mask_ratio"] == 250 / 20000
    assert row["table_area_ratio"] == 5000 / 20000
    assert row["equation_area_ratio"] == 2000 / 20000
    assert row["dominant_script"] in {"latin", "symbols"}
    assert "photometric" in row["aug_ops"]


def test_collect_feature_rows_reads_all_annotation_jsons(tmp_path):
    ann_dir = tmp_path / "ann"
    ann_dir.mkdir()

    (ann_dir / "000001.json").write_text(
        json.dumps(_sample_ann("000001"), ensure_ascii=False),
        encoding="utf-8",
    )
    (ann_dir / "000002.json").write_text(
        json.dumps(_sample_ann("000002"), ensure_ascii=False),
        encoding="utf-8",
    )

    rows = collect_feature_rows(ann_dir)

    assert len(rows) == 2
    assert {r["page_id"] for r in rows} == {"000001", "000002"}


def test_collect_feature_rows_reports_broken_json_as_error_row(tmp_path):
    ann_dir = tmp_path / "ann"
    ann_dir.mkdir()

    (ann_dir / "bad.json").write_text("{not-json", encoding="utf-8")

    rows = collect_feature_rows(ann_dir)

    assert len(rows) == 1
    assert rows[0]["page_id"] == "bad"
    assert "feature-extract-failed" in rows[0]["error"]


def test_write_features_writes_jsonl_and_csv(tmp_path):
    reports_dir = tmp_path / "reports"
    rows = [
        extract_feature_row(_sample_ann("000001")),
        extract_feature_row(_sample_ann("000002")),
    ]

    write_features(reports_dir, rows)

    jsonl_path = reports_dir / "features.jsonl"
    csv_path = reports_dir / "features.csv"

    assert jsonl_path.exists()
    assert csv_path.exists()

    jsonl_lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(jsonl_lines) == 2

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        csv_rows = list(csv.DictReader(f))

    assert len(csv_rows) == 2
    assert csv_rows[0]["page_id"] == "000001"


def test_build_diversity_summary_contains_numeric_categorical_and_recommendations():
    rows = [
        extract_feature_row(_sample_ann("000001")),
        extract_feature_row(_sample_ann("000002")),
    ]

    cfg_raw = {
        "layout": {
            "layout_type_dist": {
                "single_col": 1.0,
            }
        },
        "dist": {
            "density_dist": {
                "normal": 1.0,
            },
            "noise_level_dist": {
                "clean": 1.0,
            },
            "scale_dist": {
                "dpi300": 1.0,
            },
        },
    }

    summary = build_diversity_summary(rows, cfg_raw)

    assert summary["version"] == "diversity-summary-v1"
    assert summary["page_count"] == 2
    assert "line_count" in summary["numeric"]
    assert "layout_type" in summary["categorical"]
    assert "layout_type × noise_level" in summary["joint_coverage"]
    assert "layout_type" in summary["target_vs_observed"]
    assert isinstance(summary["recommendations"], list)
    assert len(summary["recommendations"]) >= 1


def test_write_diversity_summary_csv_writes_file(tmp_path):
    rows = [
        extract_feature_row(_sample_ann("000001")),
        extract_feature_row(_sample_ann("000002")),
    ]
    summary = build_diversity_summary(rows, cfg_raw={})

    out_path = tmp_path / "reports" / "diversity_summary.csv"

    write_diversity_summary_csv(out_path, summary)

    assert out_path.exists()

    text = out_path.read_text(encoding="utf-8")
    assert "kind,field" in text
    assert "numeric,line_count" in text


def test_diversity_report_markdown_contains_main_sections():
    rows = [extract_feature_row(_sample_ann("000001"))]
    summary = build_diversity_summary(rows, cfg_raw={})

    md = diversity_report_markdown(summary)

    assert "# Diversity Report" in md
    assert "## Numeric variance summary" in md
    assert "## Categorical diversity" in md
    assert "## Joint coverage" in md
    assert "## Recommendations" in md


def test_build_dataset_card_contains_run_and_output_sections(tmp_path):
    card = build_dataset_card(
        project_name="DocSynthFab",
        version="0.1.0",
        cfg_path="configs/default.yaml",
        out_root=tmp_path / "out",
        pages_requested=10,
        pages_ok=9,
        pages_fail=1,
        seed=123,
        workers=2,
        splits={"train": 7, "val": 1, "test": 1},
        export_targets=["native", "coco"],
    )

    assert "# Generated Dataset Card" in card
    assert "- Project: `DocSynthFab`" in card
    assert "- Pages requested: `10`" in card
    assert "- Export targets: `native, coco`" in card
    assert "## Output folders" in card
    assert "## Recommended uses" in card


def test_write_run_manifest_writes_manifest_json(tmp_path):
    path = tmp_path / "reports" / "run_manifest.json"

    manifest = write_run_manifest(
        path,
        project_name="DocSynthFab",
        version="0.1.0",
        cfg_path="configs/default.yaml",
        out_root=tmp_path / "out",
        pages_requested=10,
        pages_ok=9,
        pages_fail=1,
        seed=123,
        workers=2,
        splits={"train": 7, "val": 1, "test": 1},
        export_targets=["native"],
        qc_summary={"ok": 9, "fail": 1},
    )

    assert path.exists()

    loaded = json.loads(path.read_text(encoding="utf-8"))

    assert loaded == manifest
    assert loaded["manifest_version"] == "run-manifest-v1"
    assert loaded["project_name"] == "DocSynthFab"
    assert loaded["label_schema_version"] == LABEL_SCHEMA_VERSION
    assert loaded["qc_summary"] == {"ok": 9, "fail": 1}


def test_write_dataset_reports_writes_all_report_outputs(tmp_path):
    out_root = tmp_path / "out"
    ann_dir = out_root / "ann"
    ann_dir.mkdir(parents=True)

    (ann_dir / "000001.json").write_text(
        json.dumps(_sample_ann("000001"), ensure_ascii=False),
        encoding="utf-8",
    )
    (ann_dir / "000002.json").write_text(
        json.dumps(_sample_ann("000002"), ensure_ascii=False),
        encoding="utf-8",
    )

    result = write_dataset_reports(
        out_root=out_root,
        cfg_raw={},
        cfg_path="configs/default.yaml",
        version="0.1.0",
        pages_requested=2,
        pages_ok=2,
        pages_fail=0,
        seed=123,
        workers=1,
        splits={"train": 1, "val": 1, "test": 0},
        qc_summary={"ok": 2, "fail": 0},
        project_name="DocSynthFab",
        export_targets=["native", "coco"],
    )

    reports_dir = out_root / "reports"

    assert result["reports_dir"] == str(reports_dir)
    assert result["page_count"] == 2

    expected_files = [
        "label_schema.json",
        "label_schema.md",
        "run_manifest.json",
        "dataset_card.md",
        "features.jsonl",
        "features.csv",
        "diversity_summary.json",
        "diversity_summary.csv",
        "diversity_report.md",
    ]

    for name in expected_files:
        assert (reports_dir / name).exists(), name

    assert (out_root / "exports").exists()

    manifest = json.loads((reports_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["pages_ok"] == 2
    assert manifest["export_targets"] == ["native", "coco"]

    diversity = json.loads((reports_dir / "diversity_summary.json").read_text(encoding="utf-8"))
    assert diversity["page_count"] == 2



