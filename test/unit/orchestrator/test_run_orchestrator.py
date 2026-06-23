from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from docsynthfab.cli import (
    _build_gt_export,
    _make_fallback_render,
    _normalized_split_ratios,
    _split_of,
)
from docsynthfab.cli.args import normalize_export_targets
from docsynthfab.cli.run_loop import (
    _record_failed_result,
    _record_future_exception,
    _record_success_meta,
)


# ======================================================================================
# Local fixtures
# ======================================================================================

@pytest.fixture
def dummy_cfg():
    return SimpleNamespace(
        version="docsynthfab-ds-v0.1",
        raw={
            "page": {
                "bg_color_rgb": [255, 255, 255],
            }
        },
    )


@pytest.fixture
def ann_minimal_dict():
    return {
        "version": "docsynthfab-ds-v0.1",
        "page_id": "000001",
        "size": {
            "w": 200,
            "h": 100,
            "dpi": 300,
            "page_size_name": "a4_portrait",
            "page_width_in": 8.27,
            "page_height_in": 11.69,
            "orientation": "portrait",
        },
        "meta": {
            "layout_type": "single_col",
            "density_level": "normal",
            "scale_profile": "dpi300",
            "noise_level": "clean",
            "page_family": "report",
            "_fallback": False,
            "has_table": False,
            "has_equation": False,
            "has_equation_layout": False,
            "has_figure": False,
            "mask_text_nonzero": 100,
            "mask_math_nonzero": 0,
            "math_line_count": 0,
            "equation_block_count": 0,
            "table_block_count": 0,
            "figure_block_count": 0,
            "rotation_deg": 0,
            "perspective": False,
            "book_mode": False,
            "text_mode": "words",
            "text_order": "random",
            "content_bank_json": "data/content/content_bank.json",
            "aug_trace": [],
        },
        "blocks": [
            {
                "block_id": 0,
                "block_type": "paragraph",
                "block_order": 0,
                "column_id": 0,
                "bbox": [10, 20, 100, 40],
            }
        ],
        "lines": [
            {
                "line_id": 0,
                "block_id": 0,
                "line_type": "text",
                "line_order_in_block": 0,
                "global_line_order": 0,
                "bbox": [10, 20, 80, 20],
                "gt_text": "Hello world",
                "gt_script": "latin",
            }
        ],
        "gt_page_text": "Hello world",
        "gt_stats": {
            "line_count": 1,
        },
    }


@pytest.fixture
def ann_math_dict(ann_minimal_dict):
    ann = dict(ann_minimal_dict)
    ann["meta"] = dict(ann_minimal_dict["meta"])
    ann["lines"] = [
        {
            "line_id": 0,
            "block_id": 0,
            "line_type": "math",
            "line_order_in_block": 0,
            "global_line_order": 0,
            "bbox": [10, 20, 100, 30],
            "gt_latex": r"x^2 + y^2 = z^2",
        }
    ]
    ann["blocks"] = [
        {
            "block_id": 0,
            "block_type": "equation",
            "block_order": 0,
            "column_id": 0,
            "bbox": [10, 20, 100, 30],
        }
    ]
    ann["gt_page_text"] = ""
    ann["meta"]["has_equation"] = True
    ann["meta"]["has_equation_layout"] = True
    ann["meta"]["mask_math_nonzero"] = 255
    ann["meta"]["math_line_count"] = 1
    ann["meta"]["equation_block_count"] = 1
    return ann


def _load_main_module():
    return importlib.import_module("docsynthfab.cli.main")


def _make_dirs(root: Path) -> dict[str, Path]:
    return {
        "root": root,
        "images": root / "images",
        "masks": root / "masks",
        "ann": root / "ann",
        "gt": root / "gt",
        "splits": root / "splits",
        "reports": root / "reports",
        "exports": root / "exports",
        "tmp": root / "tmp",
    }


def _fake_cfg(
    *,
    out_root: Path,
    pages: int = 4,
    workers: int = 2,
    seed: int = 123,
    run_cfg: dict | None = None,
):
    raw = {
        "run": run_cfg
        or {
            "splits": {
                "train": 0.5,
                "val": 0.25,
                "test": 0.25,
            },
            "export_targets": ["native", "segformer", "coco"],
        }
    }

    return SimpleNamespace(
        raw=raw,
        out_root=str(out_root),
        pages=pages,
        workers=workers,
        seed=seed,
        version="docsynthfab-ds-v0.1",
    )


def _fake_run_result(
    *,
    root: Path,
    produced_ids: list[str] | None = None,
    ok: int | None = None,
    fail: int = 0,
    abort_reason: str | None = None,
):
    ids = produced_ids or ["000001", "000002", "000003", "000004"]

    return SimpleNamespace(
        ok=len(ids) if ok is None else ok,
        fail=fail,
        produced_ids=ids,
        qc_summary={
            "math_pages": 1,
            "math_mask_nonempty_pages": 1,
        },
        abort_reason=abort_reason,
        root_dir=root,
        run_log=root / "run.log",
    )


# ======================================================================================
# fallback.py
# ======================================================================================

def test_make_fallback_render_creates_minimal_valid_payload(dummy_cfg):
    rr = _make_fallback_render(dummy_cfg, page_id="000123", dpi=300)

    assert set(rr.keys()) == {"image_u8", "mask_text_u8", "mask_math_u8", "ann"}

    assert rr["image_u8"].dtype == np.uint8
    assert rr["mask_text_u8"].dtype == np.uint8
    assert rr["mask_math_u8"].dtype == np.uint8

    image = rr["image_u8"]
    mask_text = rr["mask_text_u8"]
    mask_math = rr["mask_math_u8"]
    ann = rr["ann"]

    assert image.shape[:2] == mask_text.shape
    assert mask_text.shape == mask_math.shape

    assert ann["page_id"] == "000123"
    assert ann["meta"]["_fallback"] is True
    assert ann["meta"]["scale_profile"] == "dpi300"
    assert ann["meta"]["mask_text_nonzero"] > 0
    assert ann["meta"]["mask_math_nonzero"] == 0
    assert ann["meta"]["has_equation"] is False
    assert ann["meta"]["has_table"] is False
    assert ann["meta"]["has_figure"] is False


def test_make_fallback_render_uses_lower_resolution_for_200dpi(dummy_cfg):
    rr = _make_fallback_render(dummy_cfg, page_id="000123", dpi=200)

    image = rr["image_u8"]
    ann = rr["ann"]

    assert image.shape[:2] == (2339, 1654)
    assert ann["size"]["w"] == 1654
    assert ann["size"]["h"] == 2339
    assert ann["size"]["dpi"] == 200
    assert ann["meta"]["scale_profile"] == "dpi200"


def test_make_fallback_render_uses_configured_background_color(dummy_cfg):
    dummy_cfg.raw["page"]["bg_color_rgb"] = [240, 241, 242]

    rr = _make_fallback_render(dummy_cfg, page_id="000123", dpi=300)

    image = rr["image_u8"]

    assert image[0, 0].tolist() == [240, 241, 242]


# ======================================================================================
# gt_export.py
# ======================================================================================

def test_build_gt_export_keeps_line_text_blocks_and_meta(ann_minimal_dict):
    gt = _build_gt_export(ann_minimal_dict)

    assert gt["version"] == "docsynthfab-ds-v0.1"
    assert gt["page_id"] == ann_minimal_dict["page_id"]

    assert gt["size"]["w"] == 200
    assert gt["size"]["h"] == 100
    assert gt["size"]["dpi"] == 300

    assert gt["meta"]["has_equation"] is False
    assert gt["meta"]["has_table"] is False
    assert gt["meta"]["layout_type"] == "single_col"

    assert gt["blocks"][0]["block_id"] == 0
    assert gt["blocks"][0]["block_type"] == "paragraph"

    assert gt["lines"][0]["text"] == "Hello world"
    assert gt["lines"][0]["script"] == "latin"
    assert gt["page_text"] == "Hello world"


def test_build_gt_export_reconstructs_page_text_when_missing(ann_minimal_dict):
    ann_minimal_dict["gt_page_text"] = ""
    ann_minimal_dict["lines"].append(
        {
            "line_id": 1,
            "block_id": 0,
            "line_type": "text",
            "line_order_in_block": 1,
            "global_line_order": 1,
            "bbox": [10, 40, 60, 20],
            "gt_text": "Second line",
            "gt_script": "latin",
        }
    )

    gt = _build_gt_export(ann_minimal_dict)

    assert gt["page_text"] == "Hello world\nSecond line"


def test_build_gt_export_reconstructs_page_text_by_global_order(ann_minimal_dict):
    ann_minimal_dict["gt_page_text"] = ""
    ann_minimal_dict["lines"] = [
        {
            "line_id": 2,
            "block_id": 0,
            "line_type": "text",
            "global_line_order": 2,
            "bbox": [10, 60, 60, 20],
            "gt_text": "Third",
            "gt_script": "latin",
        },
        {
            "line_id": 0,
            "block_id": 0,
            "line_type": "text",
            "global_line_order": 0,
            "bbox": [10, 20, 60, 20],
            "gt_text": "First",
            "gt_script": "latin",
        },
        {
            "line_id": 1,
            "block_id": 0,
            "line_type": "text",
            "global_line_order": 1,
            "bbox": [10, 40, 60, 20],
            "gt_text": "Second",
            "gt_script": "latin",
        },
    ]

    gt = _build_gt_export(ann_minimal_dict)

    assert gt["page_text"] == "First\nSecond\nThird"


def test_build_gt_export_keeps_latex_field(ann_math_dict):
    gt = _build_gt_export(ann_math_dict)

    assert gt["lines"][0]["line_type"] == "math"
    assert gt["lines"][0]["latex"] == r"x^2 + y^2 = z^2"
    assert gt["meta"]["has_equation"] is True
    assert gt["meta"]["has_equation_layout"] is True


# ======================================================================================
# splits.py
# ======================================================================================

def test_normalized_split_ratios_normalizes_sum():
    run_cfg = {"splits": {"train": 8, "val": 1, "test": 1}}

    tr, va, te = _normalized_split_ratios(run_cfg)

    assert round(tr, 6) == 0.8
    assert round(va, 6) == 0.1
    assert round(te, 6) == 0.1
    assert round(tr + va + te, 6) == 1.0


def test_normalized_split_ratios_uses_defaults_when_sum_is_zero():
    run_cfg = {"splits": {"train": 0, "val": 0, "test": 0}}

    tr, va, te = _normalized_split_ratios(run_cfg)

    assert (tr, va, te) == (0.80, 0.10, 0.10)


def test_normalized_split_ratios_uses_defaults_when_splits_missing():
    tr, va, te = _normalized_split_ratios({})

    assert (tr, va, te) == (0.80, 0.10, 0.10)


def test_split_of_assigns_train_val_test_ranges():
    run_cfg = {"splits": {"train": 0.6, "val": 0.2, "test": 0.2}}

    assert _split_of(0, 10, run_cfg) == "train"
    assert _split_of(5, 10, run_cfg) == "train"
    assert _split_of(6, 10, run_cfg) == "val"
    assert _split_of(7, 10, run_cfg) == "val"
    assert _split_of(8, 10, run_cfg) == "test"
    assert _split_of(9, 10, run_cfg) == "test"


def test_split_of_handles_zero_total_as_train_boundary_safe_case():
    run_cfg = {"splits": {"train": 0.8, "val": 0.1, "test": 0.1}}

    assert _split_of(0, 0, run_cfg) == "train"


# ======================================================================================
# args.py
# ======================================================================================

def test_normalize_export_targets_prefers_cli_export_string():
    run_cfg = {
        "export_targets": ["native"],
    }

    assert normalize_export_targets(run_cfg, " COCO, SegFormer , native ") == [
        "coco",
        "segformer",
        "native",
    ]


def test_normalize_export_targets_reads_list_from_config():
    run_cfg = {
        "export_targets": [" Native ", "COCO", "", "   "],
    }

    assert normalize_export_targets(run_cfg, "") == ["native", "coco"]


def test_normalize_export_targets_reads_comma_string_from_config():
    run_cfg = {
        "export_targets": "native, segformer, coco",
    }

    assert normalize_export_targets(run_cfg, "") == ["native", "segformer", "coco"]


def test_normalize_export_targets_falls_back_to_native_when_empty():
    assert normalize_export_targets({"export_targets": []}, "") == ["native"]
    assert normalize_export_targets({}, "   ") == ["native", "segformer", "coco"]


# ======================================================================================
# run_loop.py observability helpers
# ======================================================================================

def test_record_failed_result_writes_failed_and_errors_logs(tmp_path: Path):
    failed_log = tmp_path / "failed_pages.log"
    errors_log = tmp_path / "errors.jsonl"

    qc_summary = {"errors": {}}

    with (
        failed_log.open("a", encoding="utf-8") as failed_f,
        errors_log.open("a", encoding="utf-8") as err_f,
    ):
        _record_failed_result(
            pid_hint="000003",
            result={
                "ok": False,
                "error": "synthetic failed result",
                "stage": "render",
            },
            qc_summary=qc_summary,
            failed_f=failed_f,
            err_f=err_f,
        )

    failed_text = failed_log.read_text(encoding="utf-8")
    err_lines = errors_log.read_text(encoding="utf-8").splitlines()

    assert "000003" in failed_text
    assert "synthetic failed result" in failed_text
    assert qc_summary["errors"]["runtime/fatal"] == 1

    rec = json.loads(err_lines[0])

    assert rec["page_id"] == "000003"
    assert rec["err_code"] == "runtime/fatal"
    assert "synthetic failed result" in str(rec["detail"])


def test_record_future_exception_writes_traceback_and_error_detail(tmp_path: Path):
    failed_log = tmp_path / "failed_pages.log"
    errors_log = tmp_path / "errors.jsonl"

    qc_summary = {"errors": {}}

    try:
        raise RuntimeError("intentional observability failure")
    except RuntimeError as exc:
        with (
            failed_log.open("a", encoding="utf-8") as failed_f,
            errors_log.open("a", encoding="utf-8") as err_f,
        ):
            _record_future_exception(
                pid_hint="000004",
                exc=exc,
                qc_summary=qc_summary,
                failed_f=failed_f,
                err_f=err_f,
            )

    failed_text = failed_log.read_text(encoding="utf-8")
    err_lines = errors_log.read_text(encoding="utf-8").splitlines()

    assert "000004" in failed_text
    assert "intentional observability failure" in failed_text
    assert qc_summary["errors"]["runtime/exception"] == 1

    rec = json.loads(err_lines[0])

    assert rec["page_id"] == "000004"
    assert rec["err_code"] == "runtime/exception"
    assert "intentional observability failure" in rec["detail"]
    assert "RuntimeError" in rec["traceback"]


def test_record_success_meta_updates_density_scale_math_recovery_and_fallback(
    tmp_path: Path,
):
    errors_log = tmp_path / "errors.jsonl"

    qc_summary = {
        "errors": {},
        "density": {},
        "scale": {},
        "recovered": 0,
        "fallback_used": 0,
        "math_pages": 0,
        "math_layout_pages": 0,
        "math_mask_nonempty_pages": 0,
    }

    result = {
        "meta": {
            "density_level": "dense",
            "scale_profile": "dpi300",
            "has_equation": True,
            "has_equation_layout": True,
            "mask_math_nonzero": 123,
        },
        "recovered_from": [
            {
                "attempt": 1,
                "kind": "qc_fail",
                "code": "qc/example",
            }
        ],
        "fallback_used": True,
        "last_traceback": "traceback text",
    }

    with errors_log.open("a", encoding="utf-8") as err_f:
        _record_success_meta(
            pid="000005",
            result=result,
            qc_summary=qc_summary,
            err_f=err_f,
        )

    assert qc_summary["density"]["dense"] == 1
    assert qc_summary["scale"]["dpi300"] == 1
    assert qc_summary["math_pages"] == 1
    assert qc_summary["math_layout_pages"] == 1
    assert qc_summary["math_mask_nonempty_pages"] == 1
    assert qc_summary["recovered"] == 1
    assert qc_summary["fallback_used"] == 1

    records = [
        json.loads(line)
        for line in errors_log.read_text(encoding="utf-8").splitlines()
    ]

    assert records[0]["page_id"] == "000005"
    assert records[0]["err_code"] == "runtime/recovered"

    assert records[1]["page_id"] == "000005"
    assert records[1]["err_code"] == "runtime/fallback_traceback"
    assert records[1]["detail"] == "traceback text"


# ======================================================================================
# main.py CLI service orchestrator
# ======================================================================================

def test_main_runs_generation_loop_writes_splits_reports_exports_and_done_line(
    tmp_path: Path,
    monkeypatch,
):
    mod = _load_main_module()

    import docsynthfab.cli as cli_pkg

    config_path = tmp_path / "default.yaml"
    config_path.write_text("dummy: true\n", encoding="utf-8")

    out_root = tmp_path / "out"
    dirs = _make_dirs(out_root)

    calls: dict[str, object] = {
        "run_loop": None,
        "reports": None,
        "exports": None,
    }

    monkeypatch.setattr(
        mod,
        "parse_cli_args",
        lambda argv: SimpleNamespace(
            config=str(config_path),
            out=str(out_root),
            pages=4,
            workers=2,
            seed=777,
            export="coco,native",
        ),
    )

    monkeypatch.setattr(
        cli_pkg,
        "load_config",
        lambda path: _fake_cfg(
            out_root=out_root,
            pages=99,
            workers=99,
            seed=99,
        ),
    )

    monkeypatch.setattr(cli_pkg, "ensure_dataset_dirs", lambda root: dirs)

    def fake_run_generation_loop(**kwargs):
        calls["run_loop"] = kwargs
        return _fake_run_result(root=out_root)

    def fake_write_reports_safely(**kwargs):
        calls["reports"] = kwargs

    def fake_write_exports_safely(**kwargs):
        calls["exports"] = kwargs

    monkeypatch.setattr(mod, "run_generation_loop", fake_run_generation_loop)
    monkeypatch.setattr(mod, "write_reports_safely", fake_write_reports_safely)
    monkeypatch.setattr(mod, "write_exports_safely", fake_write_exports_safely)

    mod.main(["ignored"])

    run_call = calls["run_loop"]

    assert run_call is not None
    assert run_call["total"] == 4
    assert run_call["workers"] == 2
    assert run_call["seed"] == 777
    assert run_call["cfg_path"] == str(config_path.resolve())
    assert run_call["dirs"] == dirs

    assert (out_root / "splits" / "train.txt").read_text(encoding="utf-8") == "000001\n000002\n"
    assert (out_root / "splits" / "val.txt").read_text(encoding="utf-8") == "000003\n"
    assert (out_root / "splits" / "test.txt").read_text(encoding="utf-8") == "000004\n"

    reports_call = calls["reports"]

    assert reports_call is not None
    assert reports_call["out_root"] == out_root
    assert reports_call["cfg_path"] == str(config_path.resolve())
    assert reports_call["pages_requested"] == 4
    assert reports_call["pages_ok"] == 4
    assert reports_call["pages_fail"] == 0
    assert reports_call["seed"] == 777
    assert reports_call["workers"] == 2
    assert reports_call["splits"] == {
        "train": 2,
        "val": 1,
        "test": 1,
    }
    assert reports_call["export_targets"] == ["coco", "native"]

    exports_call = calls["exports"]

    assert exports_call is not None
    assert exports_call["out_root"] == out_root
    assert exports_call["export_targets"] == ["coco", "native"]

    run_log_text = (out_root / "run.log").read_text(encoding="utf-8")

    assert "done total=4 ok=4 fail=0 seed=777 workers=2" in run_log_text
    assert "abort_reason=None" in run_log_text
    assert "math_pages=1" in run_log_text
    assert "math_mask_nonempty_pages=1" in run_log_text


def test_main_uses_config_values_when_cli_overrides_are_empty(
    tmp_path: Path,
    monkeypatch,
):
    mod = _load_main_module()

    import docsynthfab.cli as cli_pkg

    config_path = tmp_path / "default.yaml"
    config_path.write_text("dummy: true\n", encoding="utf-8")

    out_root = tmp_path / "cfg_out"
    dirs = _make_dirs(out_root)

    calls: dict[str, object] = {}

    monkeypatch.setattr(
        mod,
        "parse_cli_args",
        lambda argv: SimpleNamespace(
            config=str(config_path),
            out="",
            pages=0,
            workers=0,
            seed=-1,
            export="",
        ),
    )

    monkeypatch.setattr(
        cli_pkg,
        "load_config",
        lambda path: _fake_cfg(
            out_root=out_root,
            pages=3,
            workers=5,
            seed=321,
            run_cfg={
                "splits": {
                    "train": 1,
                    "val": 0,
                    "test": 0,
                },
                "export_targets": ["segformer"],
            },
        ),
    )

    monkeypatch.setattr(cli_pkg, "ensure_dataset_dirs", lambda root: dirs)

    def fake_run_generation_loop(**kwargs):
        calls["run_loop"] = kwargs
        return _fake_run_result(
            root=out_root,
            produced_ids=["000001", "000002", "000003"],
        )

    monkeypatch.setattr(mod, "run_generation_loop", fake_run_generation_loop)
    monkeypatch.setattr(
        mod,
        "write_reports_safely",
        lambda **kwargs: calls.setdefault("reports", kwargs),
    )
    monkeypatch.setattr(
        mod,
        "write_exports_safely",
        lambda **kwargs: calls.setdefault("exports", kwargs),
    )

    mod.main([])

    assert calls["run_loop"]["total"] == 3
    assert calls["run_loop"]["workers"] == 5
    assert calls["run_loop"]["seed"] == 321

    assert (out_root / "splits" / "train.txt").read_text(encoding="utf-8") == (
        "000001\n000002\n000003\n"
    )
    assert (out_root / "splits" / "val.txt").read_text(encoding="utf-8") == ""
    assert (out_root / "splits" / "test.txt").read_text(encoding="utf-8") == ""

    assert calls["reports"]["export_targets"] == ["segformer"]
    assert calls["exports"]["export_targets"] == ["segformer"]


def test_main_forces_workers_to_one_when_config_workers_is_invalid(
    tmp_path: Path,
    monkeypatch,
):
    mod = _load_main_module()

    import docsynthfab.cli as cli_pkg

    config_path = tmp_path / "default.yaml"
    config_path.write_text("dummy: true\n", encoding="utf-8")

    out_root = tmp_path / "out"
    dirs = _make_dirs(out_root)

    calls: dict[str, object] = {}

    monkeypatch.setattr(
        mod,
        "parse_cli_args",
        lambda argv: SimpleNamespace(
            config=str(config_path),
            out=str(out_root),
            pages=2,
            workers=0,
            seed=1,
            export="",
        ),
    )

    monkeypatch.setattr(
        cli_pkg,
        "load_config",
        lambda path: _fake_cfg(
            out_root=out_root,
            pages=2,
            workers=0,
            seed=1,
        ),
    )

    monkeypatch.setattr(cli_pkg, "ensure_dataset_dirs", lambda root: dirs)

    def fake_run_generation_loop(**kwargs):
        calls["run_loop"] = kwargs
        return _fake_run_result(root=out_root, produced_ids=["000001", "000002"])

    monkeypatch.setattr(mod, "run_generation_loop", fake_run_generation_loop)
    monkeypatch.setattr(mod, "write_reports_safely", lambda **kwargs: None)
    monkeypatch.setattr(mod, "write_exports_safely", lambda **kwargs: None)

    mod.main([])

    assert calls["run_loop"]["workers"] == 1


def test_main_raises_system_exit_when_total_pages_is_invalid(
    tmp_path: Path,
    monkeypatch,
):
    mod = _load_main_module()

    import docsynthfab.cli as cli_pkg

    config_path = tmp_path / "default.yaml"
    config_path.write_text("dummy: true\n", encoding="utf-8")

    out_root = tmp_path / "out"
    dirs = _make_dirs(out_root)

    monkeypatch.setattr(
        mod,
        "parse_cli_args",
        lambda argv: SimpleNamespace(
            config=str(config_path),
            out=str(out_root),
            pages=0,
            workers=1,
            seed=1,
            export="",
        ),
    )

    monkeypatch.setattr(
        cli_pkg,
        "load_config",
        lambda path: _fake_cfg(
            out_root=out_root,
            pages=0,
            workers=1,
            seed=1,
        ),
    )

    monkeypatch.setattr(cli_pkg, "ensure_dataset_dirs", lambda root: dirs)

    with pytest.raises(SystemExit) as exc:
        mod.main([])

    assert str(exc.value) == "run/invalid-pages"


def test_main_still_writes_reports_exports_then_raises_abort_reason(
    tmp_path: Path,
    monkeypatch,
):
    mod = _load_main_module()

    import docsynthfab.cli as cli_pkg

    config_path = tmp_path / "default.yaml"
    config_path.write_text("dummy: true\n", encoding="utf-8")

    out_root = tmp_path / "out"
    dirs = _make_dirs(out_root)

    calls = {
        "reports": 0,
        "exports": 0,
    }

    monkeypatch.setattr(
        mod,
        "parse_cli_args",
        lambda argv: SimpleNamespace(
            config=str(config_path),
            out=str(out_root),
            pages=2,
            workers=1,
            seed=1,
            export="native",
        ),
    )

    monkeypatch.setattr(
        cli_pkg,
        "load_config",
        lambda path: _fake_cfg(
            out_root=out_root,
            pages=2,
            workers=1,
            seed=1,
        ),
    )

    monkeypatch.setattr(cli_pkg, "ensure_dataset_dirs", lambda root: dirs)

    monkeypatch.setattr(
        mod,
        "run_generation_loop",
        lambda **kwargs: _fake_run_result(
            root=out_root,
            produced_ids=["000001"],
            ok=1,
            fail=1,
            abort_reason="run/fail-fast-triggered",
        ),
    )

    def fake_reports(**kwargs):
        calls["reports"] += 1

    def fake_exports(**kwargs):
        calls["exports"] += 1

    monkeypatch.setattr(mod, "write_reports_safely", fake_reports)
    monkeypatch.setattr(mod, "write_exports_safely", fake_exports)

    with pytest.raises(SystemExit) as exc:
        mod.main([])

    assert str(exc.value) == "run/fail-fast-triggered"
    assert calls["reports"] == 1
    assert calls["exports"] == 1

    run_log_text = (out_root / "run.log").read_text(encoding="utf-8")

    assert "abort_reason=run/fail-fast-triggered" in run_log_text