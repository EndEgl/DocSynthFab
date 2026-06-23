# Generated Dataset Card

## Generator

- Project: `DocSynthFab`
- Version: `docsynthfab-ds-v0.1-clean-train`
- Label schema: `document-ai-label-schema-v1`
- Created at: `2026-06-23T17:04:14+00:00`

## Run

- Config path: `C:\Users\AG Zaferi\Desktop\LLM_tabanlı_projeler\DocSynthFab\.ai1_orchestrator\c12a5f6a3d6f\effective_config.yaml`
- Output root: `C:\Users\AG Zaferi\Desktop\LLM_tabanlı_projeler\DocSynthFab\test_artifacts\e2e\mathematical_diversity_50_pages`
- Pages requested: `50`
- Pages OK: `50`
- Pages failed: `0`
- Seed: `20260527`
- Workers: `1`
- Splits: `{"train": 40, "val": 5, "test": 5}`
- Export targets: `native, segformer, coco`

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
