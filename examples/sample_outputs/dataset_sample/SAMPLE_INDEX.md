# Sample Output Index

This index summarizes the selected early-alpha sample outputs.

| Page ID | Layout | Density | Noise | Family | Lines | Blocks | Scripts | Table |
|---|---|---|---|---|---:|---:|---:|---|
| 000016 | single_col | normal | clean | notes | 130 | 12 | 8 | True |
| 000012 | double_col | normal | clean | notes | 124 | 12 | 8 | True |
| 000019 | double_col | normal | medium | academic | 136 | 13 | 4 | True |
| 000094 | single_col | normal | clean | book | 75 | 13 | 9 | True |
| 000057 | mixed_cols | normal | clean | notes | 95 | 9 | 6 | True |
| 000006 | mixed_cols | sparse | clean | report | 86 | 13 | 6 | True |

Files are organized as:

```text
images/         Generated document images.
gt/             Ground truth JSON files.
ann/            Annotation JSON files.
bbox_overlays/  Visual previews with block and line bounding boxes.
reports/        QC and candidate selection metadata.
```

These samples are not formal benchmark results. They are intended to demonstrate layout diversity, multilingual rendering, and dataset packaging.