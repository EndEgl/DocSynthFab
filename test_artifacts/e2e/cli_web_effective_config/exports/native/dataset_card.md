# Generated Dataset Card

## Generator

- Project: `DocSynthFab`
- Version: `docsynthfab-ds-v0.1-clean-train`
- Label schema: `document-ai-label-schema-v1`
- Created at: `2026-06-23T17:04:38+00:00`

## Run

- Config path: `C:\Users\AG Zaferi\Desktop\LLM_tabanlı_projeler\DocSynthFab\test_artifacts\e2e\cli_web_effective_config\web_style_effective_config.yaml`
- Output root: `C:\Users\AG Zaferi\Desktop\LLM_tabanlı_projeler\DocSynthFab\test_artifacts\e2e\cli_web_effective_config`
- Pages requested: `1`
- Pages OK: `1`
- Pages failed: `0`
- Seed: `20260529`
- Workers: `1`
- Splits: `{"train": 1, "val": 0, "test": 0}`
- Export targets: `native`

## Output folders

- `images/`: generated page images
- `masks/`: generated segmentation masks
- `ann/`: full annotation JSON files
- `gt/`: ground-truth export JSON files
- `splits/`: train/val/test page id lists
- `reports/`: schema, run manifest, feature table, and diversity report
- `exports/`: model-specific export packages

## Recommended uses

- Synthetic OCR and Document AI experiments
- Text/table/math region segmentation
- Layout detection
- OCR line recognition after crop export
- LaTeX/math region experiments

## Not recommended uses

- Claiming real-world OCR quality without real validation data
- Replacing domain-specific evaluation
- Treating synthetic diversity as automatically useful without benchmark checks
