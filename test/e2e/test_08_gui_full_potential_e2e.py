# test/e2e/test_08_gui_full_potential_e2e.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - pytest>=7,<9
# - PySide6>=6.5,<7.0
# - pytest-qt>=4.4,<5.0
# - numpy>=1.24,<3.0
#
# Purpose:
# - Test GUI's real potential, not only backend overrides.
# - Change GUI controls, build RunRequest through the GUI, generate data,
#   then measure whether output distribution changes mathematically.

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from acceptance_report import append_metric_record
from e2e_support import fresh_output_dir, wait_for_run
from quality_metrics import measure_feature_mode_ratios


def _set_widget_value(widget: Any, value: Any) -> bool:
    if widget is None:
        return False

    if hasattr(widget, "setValue"):
        widget.setValue(value)
        return True

    if hasattr(widget, "setText"):
        widget.setText(str(value))
        return True

    if hasattr(widget, "setChecked"):
        widget.setChecked(bool(value))
        return True

    if hasattr(widget, "setCurrentText"):
        widget.setCurrentText(str(value))
        return True

    if hasattr(widget, "value"):
        widget.value = value
        return True

    return False


def _set_first_existing(win: Any, names: list[str], value: Any) -> str | None:
    for name in names:
        if hasattr(win, name):
            widget = getattr(win, name)
            if _set_widget_value(widget, value):
                return name

    return None


def _set_optional_combo(win: Any, names: list[str], value: str) -> str | None:
    for name in names:
        if not hasattr(win, name):
            continue

        widget = getattr(win, name)

        if hasattr(widget, "setCurrentText"):
            widget.setCurrentText(value)
            return name

        if hasattr(widget, "setText"):
            widget.setText(value)
            return name

        if hasattr(widget, "value"):
            widget.value = value
            return name

    return None


def _configure_base_gui(
    *,
    win: Any,
    config_path: Path,
    out_root: Path,
    pages: int,
    seed: int,
) -> dict[str, Any]:
    covered: dict[str, Any] = {}

    covered["config_path"] = _set_first_existing(
        win,
        ["config_path_edit", "config_path_input", "config_edit"],
        str(config_path),
    )
    covered["out_root"] = _set_first_existing(
        win,
        ["out_root_edit", "out_root_input", "output_dir_edit", "output_root_edit"],
        str(out_root),
    )
    covered["pages"] = _set_first_existing(
        win,
        ["pages_spin", "pages_input", "page_count_spin"],
        pages,
    )
    covered["workers"] = _set_first_existing(
        win,
        ["workers_spin", "workers_input"],
        1,
    )
    covered["seed"] = _set_first_existing(
        win,
        ["seed_spin", "seed_input"],
        seed,
    )
    covered["smoke"] = _set_first_existing(
        win,
        ["smoke_checkbox", "smoke_test_checkbox", "smoke_test_input"],
        False,
    )

    return covered


def _configure_ratio_gui(
    *,
    win: Any,
    text: float,
    table: float,
    latex: float,
) -> dict[str, Any]:
    covered: dict[str, Any] = {}

    covered["text_mix"] = _set_first_existing(
        win,
        ["text_mix_spin", "text_ratio_spin", "text_weight_spin", "text_mix_input"],
        text,
    )
    covered["table_mix"] = _set_first_existing(
        win,
        ["table_mix_spin", "table_ratio_spin", "table_weight_spin", "table_mix_input"],
        table,
    )
    covered["latex_mix"] = _set_first_existing(
        win,
        ["latex_mix_spin", "latex_ratio_spin", "math_mix_spin", "latex_weight_spin"],
        latex,
    )

    return covered


def _configure_preset_gui(
    *,
    win: Any,
    template: str,
    density: str,
    diversity: str,
    text_length: str,
) -> dict[str, Any]:
    """
    Optional GUI controls.

    These names intentionally include several likely variants so the test can
    measure GUI surface coverage without being brittle across refactors.
    """
    covered: dict[str, Any] = {}

    covered["template"] = _set_optional_combo(
        win,
        [
            "document_template_combo",
            "template_combo",
            "document_template_select",
            "template_select",
            "page_template_combo",
        ],
        template,
    )
    covered["density"] = _set_optional_combo(
        win,
        [
            "density_combo",
            "density_preset_combo",
            "density_select",
            "layout_density_combo",
        ],
        density,
    )
    covered["diversity"] = _set_optional_combo(
        win,
        [
            "diversity_strength_combo",
            "diversity_combo",
            "diversity_select",
            "diversity_preset_combo",
        ],
        diversity,
    )
    covered["text_length"] = _set_optional_combo(
        win,
        [
            "text_length_combo",
            "text_length_preset_combo",
            "text_block_length_combo",
            "content_length_combo",
        ],
        text_length,
    )

    return covered


def _coverage_score(covered: dict[str, Any]) -> float:
    if not covered:
        return 0.0

    return sum(1 for v in covered.values() if v) / float(len(covered))


def _run_desktop_gui_profile(
    *,
    qtbot,
    e2e_default_config: Path,
    e2e_out_root: Path,
    profile_name: str,
    text: float,
    table: float,
    latex: float,
    template: str,
    density: str,
    diversity: str,
    text_length: str,
    seed: int,
    pages: int = 20,
) -> dict[str, Any]:
    import ai1_gen.gui.desktop.app as desktop_mod
    from ai1_gen.orchestrator import RunRequest

    out_root = fresh_output_dir(e2e_out_root / profile_name)

    win = desktop_mod.DesktopMainWindow()
    qtbot.addWidget(win)

    base_covered = _configure_base_gui(
        win=win,
        config_path=e2e_default_config,
        out_root=out_root,
        pages=pages,
        seed=seed,
    )
    ratio_covered = _configure_ratio_gui(
        win=win,
        text=text,
        table=table,
        latex=latex,
    )
    preset_covered = _configure_preset_gui(
        win=win,
        template=template,
        density=density,
        diversity=diversity,
        text_length=text_length,
    )

    run_input = win.build_run_input()

    req = RunRequest(
        config_path=run_input.config_path,
        out_root=run_input.out_root,
        pages=run_input.pages,
        workers=run_input.workers,
        seed=run_input.seed,
        smoke_test=run_input.smoke_test,
        overrides={
            **run_input.overrides,
            "run.export_targets": ["native"],
        },
    )

    run_id = win.orchestrator.start(req)
    status = wait_for_run(win.orchestrator, run_id, timeout_s=600.0)

    assert str(getattr(status, "state", "")) in {"done", "completed"}

    metrics = measure_feature_mode_ratios(out_root)

    all_covered = {
        **{f"base_{k}": v for k, v in base_covered.items()},
        **{f"ratio_{k}": v for k, v in ratio_covered.items()},
        **{f"preset_{k}": v for k, v in preset_covered.items()},
    }

    metrics.update(
        {
            "profile_name": profile_name,
            "requested_text": text,
            "requested_table": table,
            "requested_latex": latex,
            "requested_template": template,
            "requested_density": density,
            "requested_diversity": diversity,
            "requested_text_length": text_length,
            "gui_base_control_coverage": _coverage_score(base_covered),
            "gui_ratio_control_coverage": _coverage_score(ratio_covered),
            "gui_preset_control_coverage": _coverage_score(preset_covered),
            "gui_total_control_coverage": _coverage_score(all_covered),
            "gui_override_count": len(run_input.overrides),
            "gui_covered_controls": {k: v for k, v in all_covered.items() if v},
            "gui_missing_controls": [k for k, v in all_covered.items() if not v],
        }
    )

    return metrics


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _text_heavy_quality(profile: dict[str, Any]) -> float:
    """
    Text-heavy should mean:
    - table dominance is low
    - math/latex dominance is low
    - text is still present

    Do not rely only on text_line_ratio, because table cells are also text lines.
    """
    text_line_ratio = float(profile.get("text_line_ratio", 0.0))
    table_block_ratio = float(profile.get("table_block_ratio", 0.0))
    table_area_ratio = float(profile.get("table_area_ratio_mean", 0.0))
    math_line_ratio = float(profile.get("math_line_ratio", 0.0))

    low_table_blocks_score = _clamp01(1.0 - table_block_ratio / 0.35)
    low_table_area_score = _clamp01(1.0 - table_area_ratio / 0.15)
    low_math_score = _clamp01(1.0 - math_line_ratio / 0.12)
    text_present_score = _clamp01(text_line_ratio / 0.85)

    return _clamp01(
        0.35 * low_table_blocks_score
        + 0.25 * low_table_area_score
        + 0.25 * low_math_score
        + 0.15 * text_present_score
    )


def _effect_score(
    *,
    text_heavy: dict[str, Any],
    table_heavy: dict[str, Any],
    latex_heavy: dict[str, Any],
    mixed: dict[str, Any],
) -> dict[str, Any]:
    text_heavy_quality = _text_heavy_quality(text_heavy)
    table_heavy_as_text_quality = _text_heavy_quality(table_heavy)
    latex_heavy_as_text_quality = _text_heavy_quality(latex_heavy)

    text_quality_delta_vs_table = text_heavy_quality - table_heavy_as_text_quality
    text_quality_delta_vs_latex = text_heavy_quality - latex_heavy_as_text_quality

    text_effect_score = _clamp01(
        0.60 * text_heavy_quality
        + 0.25 * _clamp01(text_quality_delta_vs_table / 0.20)
        + 0.15 * _clamp01(text_quality_delta_vs_latex / 0.20)
    )

    table_block_delta = (
        float(table_heavy.get("table_block_ratio", 0.0))
        - float(text_heavy.get("table_block_ratio", 0.0))
    )

    table_area_delta = (
        float(table_heavy.get("table_area_ratio_mean", 0.0))
        - float(text_heavy.get("table_area_ratio_mean", 0.0))
    )

    latex_math_delta = (
        float(latex_heavy.get("math_line_ratio", 0.0))
        - float(text_heavy.get("math_line_ratio", 0.0))
    )

    latex_presence_delta = (
        float(latex_heavy.get("latex_presence_ratio", 0.0))
        - float(text_heavy.get("latex_presence_ratio", 0.0))
    )

    mixed_balance_score = (
        float(float(mixed.get("text_line_ratio", 0.0)) > 0.30)
        + float(float(mixed.get("table_presence_ratio", 0.0)) > 0.30)
        + float(float(mixed.get("latex_presence_ratio", 0.0)) > 0.30)
    ) / 3.0

    table_effect_score = _clamp01(max(table_block_delta, table_area_delta) / 0.10)
    latex_effect_score = _clamp01(max(latex_math_delta, latex_presence_delta) / 0.10)

    avg_gui_ratio_control_coverage = (
        float(text_heavy.get("gui_ratio_control_coverage", 0.0))
        + float(table_heavy.get("gui_ratio_control_coverage", 0.0))
        + float(latex_heavy.get("gui_ratio_control_coverage", 0.0))
        + float(mixed.get("gui_ratio_control_coverage", 0.0))
    ) / 4.0

    avg_gui_preset_control_coverage = (
        float(text_heavy.get("gui_preset_control_coverage", 0.0))
        + float(table_heavy.get("gui_preset_control_coverage", 0.0))
        + float(latex_heavy.get("gui_preset_control_coverage", 0.0))
        + float(mixed.get("gui_preset_control_coverage", 0.0))
    ) / 4.0

    profile_effect_score = _clamp01(
        0.25 * text_effect_score
        + 0.25 * table_effect_score
        + 0.25 * latex_effect_score
        + 0.15 * mixed_balance_score
        + 0.10 * _clamp01(avg_gui_ratio_control_coverage)
    )

    return {
        "text_heavy_text_line_ratio": text_heavy.get("text_line_ratio", 0.0),
        "table_heavy_text_line_ratio": table_heavy.get("text_line_ratio", 0.0),
        "text_line_delta_raw": (
            float(text_heavy.get("text_line_ratio", 0.0))
            - float(table_heavy.get("text_line_ratio", 0.0))
        ),

        "text_heavy_quality": text_heavy_quality,
        "table_heavy_as_text_quality": table_heavy_as_text_quality,
        "latex_heavy_as_text_quality": latex_heavy_as_text_quality,
        "text_quality_delta_vs_table": text_quality_delta_vs_table,
        "text_quality_delta_vs_latex": text_quality_delta_vs_latex,
        "text_effect_score": text_effect_score,

        "text_heavy_table_block_ratio": text_heavy.get("table_block_ratio", 0.0),
        "table_heavy_table_block_ratio": table_heavy.get("table_block_ratio", 0.0),
        "table_block_delta": table_block_delta,

        "text_heavy_table_area_ratio_mean": text_heavy.get("table_area_ratio_mean", 0.0),
        "table_heavy_table_area_ratio_mean": table_heavy.get("table_area_ratio_mean", 0.0),
        "table_area_delta": table_area_delta,
        "table_effect_score": table_effect_score,

        "text_heavy_math_line_ratio": text_heavy.get("math_line_ratio", 0.0),
        "latex_heavy_math_line_ratio": latex_heavy.get("math_line_ratio", 0.0),
        "latex_math_delta": latex_math_delta,

        "text_heavy_latex_presence_ratio": text_heavy.get("latex_presence_ratio", 0.0),
        "latex_heavy_latex_presence_ratio": latex_heavy.get("latex_presence_ratio", 0.0),
        "latex_presence_delta": latex_presence_delta,
        "latex_effect_score": latex_effect_score,

        "mixed_text_line_ratio": mixed.get("text_line_ratio", 0.0),
        "mixed_table_presence_ratio": mixed.get("table_presence_ratio", 0.0),
        "mixed_latex_presence_ratio": mixed.get("latex_presence_ratio", 0.0),
        "mixed_balance_score": mixed_balance_score,

        "avg_gui_ratio_control_coverage": avg_gui_ratio_control_coverage,
        "avg_gui_preset_control_coverage": avg_gui_preset_control_coverage,
        "profile_effect_score": profile_effect_score,
    }



@pytest.mark.e2e
@pytest.mark.slow
def test_desktop_gui_full_potential_ratio_template_density_metrics(
    project_root: Path,
    e2e_default_config: Path,
    e2e_out_root: Path,
    qtbot,
):
    """
    Full-potential GUI E2E.

    This test does not bypass GUI controls with direct backend overrides.
    It changes Desktop GUI controls, calls build_run_input(), runs the real
    backend, and measures whether different GUI profiles create different
    output distributions.

    The scoring intentionally treats text-heavy differently:
    text-heavy is not measured only by raw text_line_ratio because table cells
    also count as text lines. Instead, text-heavy quality means:
    - text is present,
    - table dominance is low,
    - math/latex dominance is low.
    """
    pytest.importorskip("PySide6")

    text_heavy = _run_desktop_gui_profile(
        qtbot=qtbot,
        e2e_default_config=e2e_default_config,
        e2e_out_root=e2e_out_root,
        profile_name="gui_text_heavy_20_pages",
        text=90.0,
        table=5.0,
        latex=5.0,
        template="text-heavy",
        density="normal",
        diversity="balanced",
        text_length="long",
        seed=9001,
    )

    table_heavy = _run_desktop_gui_profile(
        qtbot=qtbot,
        e2e_default_config=e2e_default_config,
        e2e_out_root=e2e_out_root,
        profile_name="gui_table_heavy_20_pages",
        text=20.0,
        table=70.0,
        latex=10.0,
        template="table-heavy",
        density="normal",
        diversity="balanced",
        text_length="balanced",
        seed=9002,
    )

    latex_heavy = _run_desktop_gui_profile(
        qtbot=qtbot,
        e2e_default_config=e2e_default_config,
        e2e_out_root=e2e_out_root,
        profile_name="gui_latex_heavy_20_pages",
        text=20.0,
        table=10.0,
        latex=70.0,
        template="latex-heavy",
        density="normal",
        diversity="balanced",
        text_length="balanced",
        seed=9003,
    )

    mixed = _run_desktop_gui_profile(
        qtbot=qtbot,
        e2e_default_config=e2e_default_config,
        e2e_out_root=e2e_out_root,
        profile_name="gui_mixed_20_pages",
        text=60.0,
        table=25.0,
        latex=15.0,
        template="mixed",
        density="normal",
        diversity="balanced",
        text_length="balanced",
        seed=9004,
    )

    effect_metrics = _effect_score(
        text_heavy=text_heavy,
        table_heavy=table_heavy,
        latex_heavy=latex_heavy,
        mixed=mixed,
    )

    metrics = {
        "text_heavy": text_heavy,
        "table_heavy": table_heavy,
        "latex_heavy": latex_heavy,
        "mixed": mixed,
        **effect_metrics,
    }

    append_metric_record(
        project_root=project_root,
        test_name="test_desktop_gui_full_potential_ratio_template_density_metrics",
        metrics=metrics,
    )

    # Hard requirement: core text/table/latex ratio controls must exist
    # and must be configurable through the Desktop GUI.
    assert effect_metrics["avg_gui_ratio_control_coverage"] == 1.0

    # Text-heavy must now pass by the corrected definition:
    # text present + low table dominance + low math/latex dominance.
    assert effect_metrics["text_heavy_quality"] >= 0.60
    assert effect_metrics["text_effect_score"] >= 0.60

    # Table-heavy and latex-heavy should strongly move the output distribution.
    assert effect_metrics["table_effect_score"] >= 0.80
    assert effect_metrics["latex_effect_score"] >= 0.80

    # GUI profile changes should produce a strong measurable effect overall.
    assert effect_metrics["profile_effect_score"] >= 0.80

    # Mixed profile should not collapse into only one content family.
    assert effect_metrics["mixed_balance_score"] >= 0.66