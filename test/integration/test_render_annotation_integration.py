from __future__ import annotations

import json
from pathlib import Path

import pytest

from integration_support import assert_basic_output_tree, wait_for_run



def _run_and_load_ann(run_orchestrator, make_run_request, out_name: str, overrides: dict):
    req = make_run_request(out_name=out_name, pages=1, workers=1, seed=123, overrides=overrides)
    run_id = run_orchestrator.start(req)
    status = wait_for_run(run_orchestrator, run_id)

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    out_root = Path(req.out_root)
    assert_basic_output_tree(out_root, expected_pages=1)

    ann_path = sorted((out_root / "ann").glob("*.json"))[0]
    return json.loads(ann_path.read_text(encoding="utf-8"))


@pytest.mark.integration
@pytest.mark.slow
def test_text_only_render_produces_text_lines(run_orchestrator, make_run_request):
    ann = _run_and_load_ann(
        run_orchestrator,
        make_run_request,
        "text_only",
        {"content.block_mix": {"text": 100, "table": 0, "latex": 0}, "render.latex.enable": False},
    )

    assert ann["lines"]
    assert "table" not in {b.get("block_type") for b in ann.get("blocks", [])}


@pytest.mark.integration
@pytest.mark.slow
def test_table_only_render_produces_table_blocks(run_orchestrator, make_run_request):
    ann = _run_and_load_ann(
        run_orchestrator,
        make_run_request,
        "table_only",
        {"content.block_mix": {"text": 0, "table": 100, "latex": 0}, "render.latex.enable": False},
    )

    assert ann.get("meta", {}).get("has_table") is True
    assert "table" in {b.get("block_type") for b in ann.get("blocks", [])}


@pytest.mark.integration
@pytest.mark.slow
def test_latex_only_render_produces_math_or_equation(run_orchestrator, make_run_request):
    ann = _run_and_load_ann(
        run_orchestrator,
        make_run_request,
        "latex_only",
        {"content.block_mix": {"text": 0, "table": 0, "latex": 100}, "render.latex.enable": True},
    )

    line_types = {ln.get("line_type") for ln in ann.get("lines", [])}
    block_types = {b.get("block_type") for b in ann.get("blocks", [])}

    assert {"math", "equation", "latex"} & (line_types | block_types)


@pytest.mark.integration
@pytest.mark.slow
def test_mixed_render_produces_schema_valid_annotation(run_orchestrator, make_run_request):
    ann = _run_and_load_ann(
        run_orchestrator,
        make_run_request,
        "mixed",
        {"content.block_mix": {"text": 60, "table": 25, "latex": 15}},
    )

    assert ann.get("version") == "ai1-ds-v1.3.2"
    assert isinstance(ann.get("size"), dict)
    assert isinstance(ann.get("meta"), dict)
    assert isinstance(ann.get("lines"), list)
    assert isinstance(ann.get("blocks"), list)


@pytest.mark.integration
@pytest.mark.slow
def test_annotation_bboxes_stay_inside_page(run_orchestrator, make_run_request):
    ann = _run_and_load_ann(
        run_orchestrator,
        make_run_request,
        "bbox_contract",
        {"content.block_mix": {"text": 80, "table": 20, "latex": 0}},
    )

    page_w = int(ann["size"]["w"])
    page_h = int(ann["size"]["h"])

    orders = []

    for item in ann.get("blocks", []) + ann.get("lines", []):
        x, y, w, h = item["bbox"]
        assert 0 <= x < page_w
        assert 0 <= y < page_h
        assert w > 0
        assert h > 0
        assert x + w <= page_w
        assert y + h <= page_h

        if "global_line_order" in item:
            orders.append(item["global_line_order"])

    assert orders == sorted(orders)