from __future__ import annotations

from pathlib import Path

import pytest

from integration_support import (
    assert_basic_output_tree,
    assert_run_succeeded,
    load_json,
    load_single_annotation,
    wait_for_run,
)


@pytest.mark.integration
@pytest.mark.slow
def test_minimal_text_generation_pipeline_writes_dataset_reports_and_exports(
    run_orchestrator,
    make_run_request,
):
    req = make_run_request(
        out_name="minimal_text_pipeline",
        pages=1,
        workers=1,
        seed=123,
        export_targets=["native"],
        overrides={
            "content.block_mix": {"text": 100, "table": 0, "latex": 0},
            "render.latex.enable": False,
            "augment.enable": False,
        },
    )

    run_id = run_orchestrator.start(req)
    status = wait_for_run(run_orchestrator, run_id, timeout_s=120.0)

    assert_run_succeeded(status)

    out_root = Path(req.out_root)
    assert_basic_output_tree(out_root, expected_pages=1)

    ann = load_single_annotation(out_root)

    assert ann["version"] == "docsynthfab-ds-v0.1"
    assert ann["page_id"]
    assert isinstance(ann["size"], dict)
    assert isinstance(ann["meta"], dict)
    assert isinstance(ann["blocks"], list)
    assert isinstance(ann["lines"], list)
    assert ann["lines"]

    page_w = int(ann["size"]["w"])
    page_h = int(ann["size"]["h"])

    for item in ann["blocks"] + ann["lines"]:
        x, y, w, h = item["bbox"]
        assert 0 <= x < page_w
        assert 0 <= y < page_h
        assert w > 0
        assert h > 0
        assert x + w <= page_w
        assert y + h <= page_h

    reports_dir = out_root / "reports"

    expected_reports = [
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

    for name in expected_reports:
        assert (reports_dir / name).exists(), name

    manifest = load_json(reports_dir / "run_manifest.json")
    assert manifest["pages_requested"] == 1
    assert manifest["pages_ok"] == 1
    assert manifest["export_targets"] == ["native"]

    diversity = load_json(reports_dir / "diversity_summary.json")
    assert diversity["page_count"] == 1

    export_summary = out_root / "exports" / "export_summary.json"
    assert export_summary.exists()