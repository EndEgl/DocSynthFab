# Diversity Report

- Created at: `2026-06-23T16:59:40+00:00`
- Page count: `3`

## Numeric variance summary

| Field | Mean | Std | Variance | Min | P50 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| line_count | 22.3333 | 13.4247 | 180.222 | 10 | 16 | 38.5 | 41 |
| block_count | 6.33333 | 4.78423 | 22.8889 | 2 | 4 | 12.1 | 13 |
| math_line_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| equation_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text_mask_ratio | 0.00646607 | 0.0030688 | 9.41755e-06 | 0.00291247 | 0.00608526 | 0.00996895 | 0.0104005 |
| math_mask_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| equation_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation_deg | 0.607648 | 0.847337 | 0.717979 | -0.343217 | 0.451528 | 1.58832 | 1.71463 |

## Categorical diversity

| Field | Unique | Entropy bits | Top counts |
|---|---:|---:|---|
| layout_type | 2 | 0.918296 | `{"double_col": 2, "single_col": 1}` |
| density_level | 1 | 0 | `{"sparse": 3}` |
| noise_level | 2 | 0.918296 | `{"clean": 2, "medium": 1}` |
| scale_profile | 2 | 0.918296 | `{"dpi300": 2, "dpi200": 1}` |
| page_family | 2 | 0.918296 | `{"report": 2, "academic": 1}` |
| dominant_script | 2 | 0.918296 | `{"unknown": 2, "latin": 1}` |
| has_table | 1 | 0 | `{"0": 3}` |
| has_equation | 1 | 0 | `{"0": 3}` |
| has_figure | 1 | 0 | `{"0": 3}` |
| fallback_used | 1 | 0 | `{"0": 3}` |

## Joint coverage

| Fields | Unique combinations | Entropy bits | Top combinations |
|---|---:|---:|---|
| layout_type × noise_level | 3 | 1.58496 | `{"double_col × medium": 1, "single_col × clean": 1, "double_col × clean": 1}` |
| density_level × has_table | 1 | 0 | `{"sparse × 0": 3}` |
| density_level × has_equation | 1 | 0 | `{"sparse × 0": 3}` |
| layout_type × has_table | 2 | 0.918296 | `{"double_col × 0": 2, "single_col × 0": 1}` |
| has_table × has_equation | 1 | 0 | `{"0 × 0": 3}` |
| dominant_script × has_equation | 2 | 0.918296 | `{"unknown × 0": 2, "latin × 0": 1}` |

## Target vs observed gap

### `layout_type`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `academic` | 0.1 | 0 | -0.1 | 0.1 |
| `double_col` | 0.26 | 0.666667 | 0.406667 | 0.406667 |
| `mixed_cols` | 0.2 | 0 | -0.2 | 0.2 |
| `report_like` | 0.08 | 0 | -0.08 | 0.08 |
| `single_col` | 0.36 | 0.333333 | -0.0266667 | 0.0266667 |

### `density_level`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `dense` | 0.18 | 0 | -0.18 | 0.18 |
| `mixed` | 0.07 | 0 | -0.07 | 0.07 |
| `normal` | 0.5 | 0 | -0.5 | 0.5 |
| `sparse` | 0.25 | 1 | 0.75 | 0.75 |

### `noise_level`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `clean` | 0.55 | 0.666667 | 0.116667 | 0.116667 |
| `heavy` | 0.1 | 0 | -0.1 | 0.1 |
| `medium` | 0.35 | 0.333333 | -0.0166667 | 0.0166667 |

### `scale_profile`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `dpi200` | 0.22 | 0.333333 | 0.113333 | 0.113333 |
| `dpi300` | 0.7 | 0.666667 | -0.0333333 | 0.0333333 |
| `hires_crop` | 0.02 | 0 | -0.02 | 0.02 |
| `lowres_capture` | 0.06 | 0 | -0.06 | 0.06 |

### `page_size_name`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `a4_landscape` | 0.08 | 0 | -0.08 | 0.08 |
| `a4_portrait` | 0.5 | 0 | -0.5 | 0.5 |
| `a5_landscape` | 0.02 | 0 | -0.02 | 0.02 |
| `a5_portrait` | 0.04 | 0 | -0.04 | 0.04 |
| `b5_landscape` | 0.02 | 0 | -0.02 | 0.02 |
| `b5_portrait` | 0.04 | 0 | -0.04 | 0.04 |
| `legal_landscape` | 0.02 | 0 | -0.02 | 0.02 |
| `legal_portrait` | 0.05 | 0 | -0.05 | 0.05 |
| `letter_landscape` | 0.05 | 0 | -0.05 | 0.05 |
| `letter_portrait` | 0.18 | 0 | -0.18 | 0.18 |
| `unknown` | 0 | 1 | 1 | 1 |


## Recommendations

| Level | Area | Finding | Recommendation |
|---|---|---|---|
| warning | tables | Observed table page ratio is low: 0.000. | Increase content.has_table_prob and inspect table QC/layout failures. |
| info | latex | Observed equation page ratio is low: 0.000. | Increase content.has_equation_prob or equation block placement diversity. |
| info | math_mask_variance | math_mask_ratio variance is very low. | Increase LaTeX expression size, equation count, or formula layout variation. |
| info | target_vs_observed:layout_type | `double_col` is over-produced; signed gap=0.407. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `mixed_cols` is under-produced; signed gap=-0.200. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `dense` is under-produced; signed gap=-0.180. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `normal` is under-produced; signed gap=-0.500. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `sparse` is over-produced; signed gap=0.750. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `a4_portrait` is under-produced; signed gap=-0.500. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `letter_portrait` is under-produced; signed gap=-0.180. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `unknown` is over-produced; signed gap=1.000. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
