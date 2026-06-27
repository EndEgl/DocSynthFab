# SegFormer / U-Net Export

This export prepares image and mask folders by split.

## Structure

- `images/train|val|test/`
- `masks_text/train|val|test/`
- `masks_math/train|val|test/`
- `class_map.json`

## Current phase

This first export preserves the existing binary masks:

- text mask
- math/LaTeX mask

A later phase can create a single multi-class semantic mask:

- 0 background
- 1 plain_text
- 2 table_region
- 3 math_latex
- 4 figure
