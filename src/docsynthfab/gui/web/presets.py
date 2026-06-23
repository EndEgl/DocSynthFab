# src/docsynthfab/gui/web/presets.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import Any, Dict, List


DATASET_GOAL_PRESETS: Dict[str, Dict[str, Any]] = {
    "Quick OCR Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "words",
    },
    "Layout + OCR Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "sentences",
    },
    "Table-heavy Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "sentences",
        "render.non_text.table_size_mix": {
            "small": 0.25,
            "medium": 0.45,
            "large": 0.30,
        },
    },
    "Full Document AI Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "sentences",
        "render.non_text.table_size_mix": {
            "small": 0.30,
            "medium": 0.45,
            "large": 0.25,
        },
    },
}


DATASET_CHARACTER_PRESETS: Dict[str, Dict[str, Any]] = {
    "Clean": {
        "dist.noise_level_dist": {
            "clean": 0.85,
            "medium": 0.15,
            "heavy": 0.00,
        },
        "augment.enable": True,
        "augment.selection_policy.clean.p_photometric": 0.15,
        "augment.selection_policy.clean.p_blur_noise": 0.05,
        "augment.selection_policy.clean.p_capture": 0.00,
        "augment.selection_policy.clean.p_geometry": 0.00,
        "augment.selection_policy.clean.p_edge": 0.00,
        "augment.selection_policy.clean.p_elastic": 0.00,
    },
    "Balanced": {
        "dist.noise_level_dist": {
            "clean": 0.35,
            "medium": 0.50,
            "heavy": 0.15,
        },
        "augment.enable": True,
    },
    "Realistic Scan": {
        "dist.noise_level_dist": {
            "clean": 0.20,
            "medium": 0.55,
            "heavy": 0.25,
        },
        "augment.enable": True,
        "augment.selection_policy.medium.p_capture": 0.45,
        "augment.selection_policy.medium.p_blur_noise": 0.35,
        "augment.selection_policy.medium.p_photometric": 0.45,
        "augment.selection_policy.medium.p_geometry": 0.20,
    },
    "Stress Test": {
        "dist.noise_level_dist": {
            "clean": 0.05,
            "medium": 0.35,
            "heavy": 0.60,
        },
        "augment.enable": True,
        "augment.selection_policy.heavy.p_capture": 0.65,
        "augment.selection_policy.heavy.p_blur_noise": 0.68,
        "augment.selection_policy.heavy.p_geometry": 0.50,
        "augment.selection_policy.heavy.p_edge": 0.45,
        "augment.selection_policy.heavy.p_elastic": 0.25,
    },
}


DIVERSITY_STRENGTH_PRESETS: Dict[str, Dict[str, Any]] = {
    "Balanced diversity": {
        "diversity_preset": "balanced_document_ai_diverse",
        "dist.noise_level_dist": {
            "clean": 0.30,
            "medium": 0.45,
            "heavy": 0.25,
        },
        "layout.layout_type_dist": {
            "single_col": 0.28,
            "double_col": 0.24,
            "mixed_cols": 0.28,
            "academic": 0.12,
            "report_like": 0.08,
        },
        "render.text.scripts_dist": {
            "latin": 0.30,
            "tr": 0.14,
            "de": 0.06,
            "ru": 0.08,
            "el": 0.05,
            "ar": 0.06,
            "he": 0.04,
            "hi": 0.05,
            "zh": 0.05,
            "ja": 0.05,
            "ko": 0.04,
            "th": 0.03,
            "symbols": 0.05,
        },
    },
    "High diversity": {
        "diversity_preset": "high_document_ai_diverse",
        "dist.noise_level_dist": {
            "clean": 0.22,
            "medium": 0.48,
            "heavy": 0.30,
        },
        "layout.layout_type_dist": {
            "single_col": 0.22,
            "double_col": 0.24,
            "mixed_cols": 0.34,
            "academic": 0.12,
            "report_like": 0.08,
        },
        "render.text.scripts_dist": {
            "latin": 0.24,
            "tr": 0.12,
            "de": 0.06,
            "ru": 0.10,
            "el": 0.06,
            "ar": 0.08,
            "he": 0.05,
            "hi": 0.06,
            "zh": 0.07,
            "ja": 0.06,
            "ko": 0.05,
            "th": 0.04,
            "symbols": 0.05,
        },
        "render.non_text.table_size_mix": {
            "small": 0.28,
            "medium": 0.42,
            "large": 0.30,
        },
    },
    "Max diversity / stress": {
        "diversity_preset": "max_document_ai_diverse_stress",
        "dist.noise_level_dist": {
            "clean": 0.15,
            "medium": 0.45,
            "heavy": 0.40,
        },
        "layout.layout_type_dist": {
            "single_col": 0.18,
            "double_col": 0.24,
            "mixed_cols": 0.38,
            "academic": 0.12,
            "report_like": 0.08,
        },
        "render.text.scripts_dist": {
            "latin": 0.20,
            "tr": 0.10,
            "de": 0.06,
            "ru": 0.11,
            "el": 0.07,
            "ar": 0.09,
            "he": 0.06,
            "hi": 0.07,
            "zh": 0.08,
            "ja": 0.07,
            "ko": 0.06,
            "th": 0.05,
            "symbols": 0.08,
        },
        "render.non_text.table_size_mix": {
            "small": 0.30,
            "medium": 0.35,
            "large": 0.35,
        },
        "augment.selection_policy.heavy.p_capture": 0.65,
        "augment.selection_policy.heavy.p_blur_noise": 0.68,
        "augment.selection_policy.heavy.p_geometry": 0.50,
        "augment.selection_policy.heavy.p_edge": 0.45,
        "augment.selection_policy.heavy.p_elastic": 0.25,
    },
}


TEXT_LENGTH_PRESETS: Dict[str, Dict[str, Any]] = {
    "Short blocks": {
        "content.text_mode": "words",
        "content.words": {
            "min_words": 3,
            "max_words": 14,
            "separator": " ",
        },
        "content.sentences": {
            "min_sentences": 1,
            "max_sentences": 2,
            "separator": " ",
        },
    },
    "Balanced blocks": {
        "content.text_mode": "words",
        "content.words": {
            "min_words": 25,
            "max_words": 90,
            "separator": " ",
        },
        "content.sentences": {
            "min_sentences": 2,
            "max_sentences": 6,
            "separator": " ",
        },
    },
    "Long paragraphs": {
        "content.text_mode": "words",
        "content.words": {
            "min_words": 80,
            "max_words": 260,
            "separator": " ",
        },
        "content.sentences": {
            "min_sentences": 5,
            "max_sentences": 14,
            "separator": " ",
        },
    },
    "Dense text": {
        "content.text_mode": "words",
        "content.words": {
            "min_words": 180,
            "max_words": 600,
            "separator": " ",
        },
        "content.sentences": {
            "min_sentences": 8,
            "max_sentences": 24,
            "separator": " ",
        },
    },
}


DOCUMENT_TEMPLATE_PRESETS: Dict[str, Dict[str, Any]] = {
    # Public/open-source first version: generic templates only.
    # Business-specific templates such as invoice, receipt, and contract are
    # intentionally kept out of the active preset surface. They can return later
    # as a separate optional template pack.
    "Generic random document": {},
}


TEMPLATE_REGION_TYPES = [
    "text_block",
    "table",
    "figure",
    "separator",
    "empty_box",
    "numbered_list",
    "bullet_list",
    "paragraph",
    "header",
    "footer",
]


TEMPLATE_COLUMNS = [
    "template_name",
    "page_no",
    "region_id",
    "type",
    "label",
    "x",
    "y",
    "w",
    "h",
    "content_source",
    "min_rows",
    "max_rows",
    "cols",
    "required",
    "jitter",
    "style_hint",
    "mask_role",
    "annotation_label",
]


SAMPLE_TEMPLATE_ROWS: List[Dict[str, Any]] = [
    {
        "template_name": "generic_layout_basic",
        "page_no": 1,
        "region_id": "header",
        "type": "header",
        "label": "page_header",
        "x": 0.05,
        "y": 0.04,
        "w": 0.90,
        "h": 0.06,
        "content_source": "word_bank",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": True,
        "jitter": 0.005,
        "style_hint": "bold_header",
        "mask_role": "text",
        "annotation_label": "header",
    },
    {
        "template_name": "generic_layout_basic",
        "page_no": 1,
        "region_id": "body",
        "type": "paragraph",
        "label": "body_text",
        "x": 0.08,
        "y": 0.16,
        "w": 0.84,
        "h": 0.32,
        "content_source": "word_bank",
        "min_rows": 4,
        "max_rows": 12,
        "cols": "",
        "required": True,
        "jitter": 0.01,
        "style_hint": "normal_block",
        "mask_role": "text",
        "annotation_label": "paragraph",
    },
    {
        "template_name": "generic_layout_basic",
        "page_no": 1,
        "region_id": "table",
        "type": "table",
        "label": "generic_table",
        "x": 0.08,
        "y": 0.54,
        "w": 0.84,
        "h": 0.28,
        "content_source": "word_bank",
        "min_rows": 3,
        "max_rows": 8,
        "cols": 4,
        "required": False,
        "jitter": 0.01,
        "style_hint": "bordered_table",
        "mask_role": "text",
        "annotation_label": "table",
    },
]



