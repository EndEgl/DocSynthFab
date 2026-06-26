"""Shared Quick Guide content for the DocSynthFab GUI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuickGuideStep:
    title: str
    text: str


QUICK_GUIDE_TITLE = "Quick Guide"

QUICK_GUIDE_SUBTITLE = (
    "Recommended first run settings for generating a small synthetic document dataset."
)

QUICK_GUIDE_STEPS = [
    QuickGuideStep(
        "1. Choose an output folder",
        "Use an empty or dedicated output folder so generated images, annotations, ground truth, masks, and reports stay together.",
    ),
    QuickGuideStep(
        "2. Start small",
        "For a first run, generate 5–20 pages. Use 1–2 workers on a normal laptop, then increase gradually if the machine stays responsive.",
    ),
    QuickGuideStep(
        "3. Pick a visual character",
        "Use Balanced or Realistic Scan for clean public samples. Use Stress Test mainly for robustness checks.",
    ),
    QuickGuideStep(
        "4. Balance text and tables",
        "For showcase samples, prefer a mix of paragraph-heavy, table-heavy, and hybrid pages instead of only table-like pages.",
    ),
    QuickGuideStep(
        "5. Check the output",
        "After generation, inspect images/, gt/, ann/, masks/, reports/, and any bbox overlay previews before using samples publicly.",
    ),
]

RECOMMENDED_FIRST_RUN = {
    "Pages": "5–20",
    "Workers": "1–2",
    "Dataset character": "Balanced or Realistic Scan",
    "Density": "Normal or Mixed",
    "Diversity": "Balanced",
    "Output folder": "Empty or dedicated folder",
}

OUTPUT_FOLDERS_TO_CHECK = [
    "images/",
    "gt/",
    "ann/",
    "masks/",
    "reports/",
    "bbox_overlays/ if exported",
]
