# src/ai1_gen/reports/label_schema.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# This module uses only the Python standard library.

from __future__ import annotations

from typing import Any, Dict


LABEL_SCHEMA_VERSION = "document-ai-label-schema-v1"


def build_label_schema() -> Dict[str, Any]:
    """
    Build the first stable generated-label schema.

    Table cells are intentionally not a separate class yet. The current stable
    contract keeps table output at table-region level. Cell-level schema can be
    added in a later phase without breaking the current label schema.
    """
    classes = [
        {
            "id": 0,
            "name": "background",
            "semantic_type": "background",
            "ocr_target_type": "ignore",
            "mask_channel": 0,
            "description": "Pixels outside document content.",
            "recommended_tasks": ["segmentation"],
            "export_targets": ["segformer", "native"],
        },
        {
            "id": 1,
            "name": "plain_text",
            "semantic_type": "plain_text",
            "ocr_target_type": "plain_text",
            "mask_channel": 1,
            "description": "Normal text such as paragraphs, titles, captions, headers, or footers.",
            "recommended_tasks": ["segmentation", "layout_detection", "ocr_recognition"],
            "export_targets": ["segformer", "coco", "yolo", "trocr", "paddleocr", "native"],
        },
        {
            "id": 2,
            "name": "table_region",
            "semantic_type": "table_region",
            "ocr_target_type": "table_structure",
            "mask_channel": 2,
            "description": "Full table region. Cell-level export can be added in a later phase.",
            "recommended_tasks": ["segmentation", "layout_detection", "table_detection"],
            "export_targets": ["segformer", "coco", "yolo", "native"],
        },
        {
            "id": 3,
            "name": "math_latex",
            "semantic_type": "math_latex",
            "ocr_target_type": "latex_formula",
            "mask_channel": 3,
            "description": "Rendered math or LaTeX formula region.",
            "recommended_tasks": ["segmentation", "layout_detection", "latex_recognition"],
            "export_targets": ["segformer", "coco", "yolo", "latex_ocr", "native"],
        },
        {
            "id": 4,
            "name": "figure",
            "semantic_type": "figure",
            "ocr_target_type": "ignore",
            "mask_channel": 4,
            "description": "Non-text figure, drawing, chart, or decorative region.",
            "recommended_tasks": ["segmentation", "layout_detection"],
            "export_targets": ["segformer", "coco", "yolo", "native"],
        },
    ]

    return {
        "schema_version": LABEL_SCHEMA_VERSION,
        "task_family": "document_ai",
        "classes": classes,
        "mask_channels": {str(c["mask_channel"]): c["name"] for c in classes},
        "recommended_task_mapping": {
            "segmentation": ["background", "plain_text", "table_region", "math_latex", "figure"],
            "layout_detection": ["plain_text", "table_region", "math_latex", "figure"],
            "ocr_recognition": ["plain_text"],
            "latex_recognition": ["math_latex"],
            "table_detection": ["table_region"],
        },
        "notes": [
            "This schema describes generated labels, not a published dataset.",
            "The generator output can be exported to model-specific formats.",
            "table_cell_text is intentionally left for the next schema phase.",
        ],
    }


def label_schema_markdown(schema: Dict[str, Any]) -> str:
    """Render the label schema as a human-readable Markdown document."""
    lines = [
        "# Label Schema",
        "",
        f"- Schema version: `{schema.get('schema_version')}`",
        f"- Task family: `{schema.get('task_family')}`",
        "",
        "| ID | Name | Semantic type | OCR target | Mask channel | Recommended tasks |",
        "|---:|---|---|---|---:|---|",
    ]

    for c in schema.get("classes", []):
        lines.append(
            "| {id} | `{name}` | `{semantic}` | `{ocr}` | {ch} | {tasks} |".format(
                id=c.get("id"),
                name=c.get("name"),
                semantic=c.get("semantic_type"),
                ocr=c.get("ocr_target_type"),
                ch=c.get("mask_channel"),
                tasks=", ".join(c.get("recommended_tasks", [])),
            )
        )

    lines.extend(
        [
            "",
            "## Usage",
            "",
            "- Segmentation models should use `mask_channel` values.",
            "- OCR recognition exports should use `plain_text` lines and `gt_text`.",
            "- LaTeX recognition exports should use `math_latex` regions and `gt_latex`.",
            "- Table structure support starts with `table_region`; cell-level schema can be added later.",
        ]
    )

    return "\n".join(lines)