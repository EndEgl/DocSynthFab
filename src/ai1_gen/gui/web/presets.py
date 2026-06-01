# src/ai1_gen/gui/web/presets.py
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
    "Math Document Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "sentences",
        "render.latex.enable": True,
    },
    "Table-heavy Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "sentences",
    },
    "Full Document AI Dataset": {
        "content.source_mode": "content_bank",
        "content.text_mode": "sentences",
        "render.latex.enable": True,
    },
}


DATASET_CHARACTER_PRESETS: Dict[str, Dict[str, Any]] = {
    "Clean": {
        "dist.noise_level_dist": {"clean": 0.85, "medium": 0.15, "heavy": 0.00},
        "augment.enable": True,
    },
    "Balanced": {
        "dist.noise_level_dist": {"clean": 0.35, "medium": 0.50, "heavy": 0.15},
        "augment.enable": True,
    },
    "Realistic Scan": {
        "dist.noise_level_dist": {"clean": 0.20, "medium": 0.55, "heavy": 0.25},
        "augment.enable": True,
    },
    "Stress Test": {
        "dist.noise_level_dist": {"clean": 0.05, "medium": 0.35, "heavy": 0.60},
        "augment.enable": True,
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
            "latin": 0.42,
            "tr": 0.20,
            "de": 0.06,
            "ru": 0.10,
            "el": 0.06,
            "ar": 0.07,
            "symbols": 0.09,
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
            "latin": 0.34,
            "tr": 0.20,
            "de": 0.07,
            "ru": 0.12,
            "el": 0.08,
            "ar": 0.09,
            "symbols": 0.10,
        },
        "render.latex.complexity_mix": {
            "simple": 0.25,
            "medium": 0.45,
            "complex": 0.30,
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
            "latin": 0.28,
            "tr": 0.18,
            "de": 0.08,
            "ru": 0.14,
            "el": 0.09,
            "ar": 0.11,
            "symbols": 0.12,
        },
        "render.latex.complexity_mix": {
            "simple": 0.18,
            "medium": 0.42,
            "complex": 0.40,
        },
        "render.non_text.table_size_mix": {
            "small": 0.30,
            "medium": 0.35,
            "large": 0.35,
        },
        "augment.selection_policy.heavy.p_capture": 0.65,
        "augment.selection_policy.heavy.p_blur_noise": 0.68,
        "augment.selection_policy.heavy.p_geometry": 0.50,
    },
}


TEXT_LENGTH_PRESETS: Dict[str, Dict[str, Any]] = {
    "Short blocks": {
        "content.text_mode": "words",
    },
    "Balanced blocks": {
        "content.text_mode": "mixed",
    },
    "Long paragraphs": {
        "content.text_mode": "sentences",
    },
}


DOCUMENT_TEMPLATE_PRESETS: Dict[str, Dict[str, Any]] = {
    "Generic random document": {},
    "Invoice": {
        "content.text_mode": "sentences",
    },
    "Delivery note": {
        "content.text_mode": "sentences",
    },
    "Customs declaration": {
        "content.text_mode": "sentences",
    },
    "Exam sheet": {
        "content.text_mode": "sentences",
        "render.latex.enable": True,
    },
    "Contract page": {
        "content.text_mode": "sentences",
    },
    "Inspection checklist": {
        "content.text_mode": "sentences",
    },
    "Custom CSV template": {},
}


TEMPLATE_REGION_TYPES = [
    "text_block",
    "field",
    "table",
    "checkbox",
    "checkbox_group",
    "signature",
    "stamp",
    "figure",
    "separator",
    "empty_box",
    "barcode_like",
    "qr_like",
    "numbered_list",
    "bullet_list",
    "paragraph",
    "math_block",
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
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "title",
        "type": "header",
        "label": "document_title",
        "x": 0.05,
        "y": 0.04,
        "w": 0.45,
        "h": 0.05,
        "content_source": "doc_titles",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": True,
        "jitter": 0.005,
        "style_hint": "bold_header",
        "mask_role": "text",
        "annotation_label": "title",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "seller",
        "type": "text_block",
        "label": "seller_info",
        "x": 0.05,
        "y": 0.11,
        "w": 0.42,
        "h": 0.12,
        "content_source": "company_info",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": True,
        "jitter": 0.01,
        "style_hint": "normal_block",
        "mask_role": "text",
        "annotation_label": "seller_info",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "invoice_no",
        "type": "field",
        "label": "invoice_number",
        "x": 0.66,
        "y": 0.05,
        "w": 0.26,
        "h": 0.04,
        "content_source": "invoice_numbers",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": True,
        "jitter": 0.005,
        "style_hint": "small_field",
        "mask_role": "text",
        "annotation_label": "invoice_number",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "items",
        "type": "table",
        "label": "items_table",
        "x": 0.05,
        "y": 0.30,
        "w": 0.90,
        "h": 0.38,
        "content_source": "product_rows",
        "min_rows": 4,
        "max_rows": 12,
        "cols": 6,
        "required": True,
        "jitter": 0.01,
        "style_hint": "bordered_table",
        "mask_role": "text",
        "annotation_label": "items_table",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "signature",
        "type": "signature",
        "label": "signature_area",
        "x": 0.62,
        "y": 0.82,
        "w": 0.28,
        "h": 0.08,
        "content_source": "signatures",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": False,
        "jitter": 0.01,
        "style_hint": "signature_box",
        "mask_role": "text",
        "annotation_label": "signature",
    },
]