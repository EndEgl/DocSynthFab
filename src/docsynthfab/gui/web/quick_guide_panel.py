"""NiceGUI Quick Guide panel for the Web GUI."""

from __future__ import annotations

from nicegui import ui

from docsynthfab.gui.shared.quick_guide import (
    OUTPUT_FOLDERS_TO_CHECK,
    QUICK_GUIDE_STEPS,
    QUICK_GUIDE_SUBTITLE,
    QUICK_GUIDE_TITLE,
    RECOMMENDED_FIRST_RUN,
)


def build_quick_guide_panel() -> None:
    """Render a compact onboarding guide for first-time GUI users."""

    with ui.expansion(QUICK_GUIDE_TITLE, icon="help_outline", value=False).classes(
        "ai-card w-full"
    ):
        ui.label(QUICK_GUIDE_SUBTITLE).classes("text-sm text-gray-600")

        with ui.grid(columns=2).classes("w-full gap-4 mt-2"):
            with ui.card().classes("w-full"):
                ui.label("Recommended first run").classes("text-base font-semibold")
                for key, value in RECOMMENDED_FIRST_RUN.items():
                    with ui.row().classes("w-full items-start gap-2"):
                        ui.label(f"{key}:").classes("text-sm font-medium text-gray-700")
                        ui.label(value).classes("text-sm text-gray-600")

            with ui.card().classes("w-full"):
                ui.label("After generation, check").classes("text-base font-semibold")
                for folder in OUTPUT_FOLDERS_TO_CHECK:
                    ui.label(f"- {folder}").classes("text-sm text-gray-600")

        ui.separator().classes("my-2")

        for step in QUICK_GUIDE_STEPS:
            ui.label(step.title).classes("text-sm font-semibold text-gray-800")
            ui.label(step.text).classes("text-sm text-gray-600 mb-1")
