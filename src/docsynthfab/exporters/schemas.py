# src/docsynthfab/exporters/schemas.py
# Recommended version ranges:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import Dict, List


# Shared semantic class map for segmentation-style exports.
CLASS_MAP: Dict[int, str] = {
    0: "background",
    1: "plain_text",
    2: "table_region",
    3: "math_latex",
    4: "figure",
}


# COCO category ids must be stable across runs.
COCO_CATEGORY_MAP: Dict[str, int] = {
    "plain_text": 1,
    "table_region": 2,
    "math_latex": 3,
    "figure": 4,
}


COCO_CATEGORIES: List[dict] = [
    {"id": 1, "name": "plain_text", "supercategory": "document"},
    {"id": 2, "name": "table_region", "supercategory": "document"},
    {"id": 3, "name": "math_latex", "supercategory": "document"},
    {"id": 4, "name": "figure", "supercategory": "document"},
]



