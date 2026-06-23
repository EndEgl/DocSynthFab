from __future__ import annotations

from pathlib import Path

import docsynthfab.exporters.dataset_exporters as mod


def test_export_dataset_package_dispatches_known_targets_and_writes_summary(
    tmp_path: Path,
    monkeypatch,
):
    calls: list[tuple[str, Path]] = []
    written: list[tuple[Path, object]] = []

    def fake_export_native(out_root: Path) -> dict:
        calls.append(("native", out_root))
        return {
            "target": "native",
            "export_root": str(out_root / "exports" / "native"),
        }

    def fake_export_segformer(out_root: Path) -> dict:
        calls.append(("segformer", out_root))
        return {
            "target": "segformer",
            "export_root": str(out_root / "exports" / "segformer"),
        }

    def fake_export_coco(out_root: Path) -> dict:
        calls.append(("coco", out_root))
        return {
            "target": "coco",
            "export_root": str(out_root / "exports" / "coco"),
        }

    def fake_write_json(path: Path, obj: object) -> None:
        written.append((path, obj))

    monkeypatch.setattr(mod, "export_native", fake_export_native)
    monkeypatch.setattr(mod, "export_segformer", fake_export_segformer)
    monkeypatch.setattr(mod, "export_coco", fake_export_coco)
    monkeypatch.setattr(mod, "write_json", fake_write_json)

    result = mod.export_dataset_package(
        out_root=tmp_path,
        targets=["native", "segformer", "coco"],
    )

    assert calls == [
        ("native", tmp_path),
        ("segformer", tmp_path),
        ("coco", tmp_path),
    ]

    assert set(result.keys()) == {"native", "segformer", "coco"}
    assert result["native"]["target"] == "native"
    assert result["segformer"]["target"] == "segformer"
    assert result["coco"]["target"] == "coco"

    assert (tmp_path / "exports").exists()

    assert len(written) == 1
    summary_path, summary_obj = written[0]

    assert summary_path == tmp_path / "exports" / "export_summary.json"
    assert summary_obj == result


def test_export_dataset_package_normalizes_target_names(
    tmp_path: Path,
    monkeypatch,
):
    calls: list[str] = []

    def fake_export_native(out_root: Path) -> dict:
        calls.append("native")
        return {"target": "native"}

    def fake_export_segformer(out_root: Path) -> dict:
        calls.append("segformer")
        return {"target": "segformer"}

    def fake_export_coco(out_root: Path) -> dict:
        calls.append("coco")
        return {"target": "coco"}

    monkeypatch.setattr(mod, "export_native", fake_export_native)
    monkeypatch.setattr(mod, "export_segformer", fake_export_segformer)
    monkeypatch.setattr(mod, "export_coco", fake_export_coco)
    monkeypatch.setattr(mod, "write_json", lambda path, obj: None)

    result = mod.export_dataset_package(
        out_root=tmp_path,
        targets=["  NATIVE  ", " SegFormer ", " COCO ", "", "   "],
    )

    assert calls == ["native", "segformer", "coco"]
    assert set(result.keys()) == {"native", "segformer", "coco"}


def test_export_dataset_package_defaults_to_native_when_targets_empty(
    tmp_path: Path,
    monkeypatch,
):
    calls: list[tuple[str, Path]] = []

    def fake_export_native(out_root: Path) -> dict:
        calls.append(("native", out_root))
        return {
            "target": "native",
            "export_root": str(out_root / "exports" / "native"),
        }

    monkeypatch.setattr(mod, "export_native", fake_export_native)
    monkeypatch.setattr(mod, "write_json", lambda path, obj: None)

    result = mod.export_dataset_package(
        out_root=tmp_path,
        targets=[],
    )

    assert calls == [("native", tmp_path)]
    assert set(result.keys()) == {"native"}
    assert result["native"]["target"] == "native"


def test_export_dataset_package_defaults_to_native_when_targets_are_blank(
    tmp_path: Path,
    monkeypatch,
):
    calls: list[str] = []

    def fake_export_native(out_root: Path) -> dict:
        calls.append("native")
        return {"target": "native"}

    monkeypatch.setattr(mod, "export_native", fake_export_native)
    monkeypatch.setattr(mod, "write_json", lambda path, obj: None)

    result = mod.export_dataset_package(
        out_root=tmp_path,
        targets=["", "   ", "\t"],
    )

    assert calls == ["native"]
    assert set(result.keys()) == {"native"}
    assert result["native"]["target"] == "native"


def test_export_dataset_package_records_unsupported_target_without_crashing(
    tmp_path: Path,
    monkeypatch,
):
    calls: list[str] = []
    written: list[tuple[Path, object]] = []

    def fake_export_native(out_root: Path) -> dict:
        calls.append("native")
        return {"target": "native"}

    def fake_write_json(path: Path, obj: object) -> None:
        written.append((path, obj))

    monkeypatch.setattr(mod, "export_native", fake_export_native)
    monkeypatch.setattr(mod, "write_json", fake_write_json)

    result = mod.export_dataset_package(
        out_root=tmp_path,
        targets=["native", "unknown_target"],
    )

    assert calls == ["native"]

    assert result["native"] == {"target": "native"}
    assert result["unknown_target"] == {
        "target": "unknown_target",
        "skipped": True,
        "reason": "unsupported-export-target",
    }

    assert len(written) == 1
    assert written[0][0] == tmp_path / "exports" / "export_summary.json"
    assert written[0][1] == result


def test_export_dataset_package_accepts_string_out_root(
    tmp_path: Path,
    monkeypatch,
):
    calls: list[Path] = []

    def fake_export_native(out_root: Path) -> dict:
        calls.append(out_root)
        return {"target": "native"}

    monkeypatch.setattr(mod, "export_native", fake_export_native)
    monkeypatch.setattr(mod, "write_json", lambda path, obj: None)

    result = mod.export_dataset_package(
        out_root=str(tmp_path),
        targets=["native"],
    )

    assert calls == [tmp_path]
    assert result["native"]["target"] == "native"