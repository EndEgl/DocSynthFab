# Label Schema

- Schema version: `document-ai-label-schema-v1`
- Task family: `document_ai`

| ID | Name | Semantic type | OCR target | Mask channel | Recommended tasks |
|---:|---|---|---|---:|---|
| 0 | `background` | `background` | `ignore` | 0 | segmentation |
| 1 | `plain_text` | `plain_text` | `plain_text` | 1 | segmentation, layout_detection, ocr_recognition |
| 2 | `table_region` | `table_region` | `table_structure` | 2 | segmentation, layout_detection, table_detection |
| 3 | `math_latex` | `math_latex` | `latex_formula` | 3 | segmentation, layout_detection, latex_recognition |
| 4 | `figure` | `figure` | `ignore` | 4 | segmentation, layout_detection |

## Usage

- Segmentation models should use `mask_channel` values.
- OCR recognition exports should use `plain_text` lines and `gt_text`.
- LaTeX recognition exports should use `math_latex` regions and `gt_latex`.
- Table structure support starts with `table_region`; cell-level schema can be added later.
