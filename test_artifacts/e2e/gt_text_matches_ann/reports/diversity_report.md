# Diversity Report

- Created at: `2026-06-23T16:58:58+00:00`
- Page count: `3`

## Numeric variance summary

| Field | Mean | Std | Variance | Min | P50 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| line_count | 31.3333 | 12.2293 | 149.556 | 19 | 27 | 45.9 | 48 |
| block_count | 5.33333 | 0.471405 | 0.222222 | 5 | 5 | 5.9 | 6 |
| math_line_count | 2.66667 | 1.24722 | 1.55556 | 1 | 3 | 3.9 | 4 |
| table_block_count | 0.666667 | 0.471405 | 0.222222 | 0 | 1 | 1 | 1 |
| equation_block_count | 1 | 0 | 0 | 1 | 1 | 1 | 1 |
| figure_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text_mask_ratio | 0.00338074 | 0.00147243 | 2.16805e-06 | 0.0013032 | 0.00429716 | 0.00451738 | 0.00454185 |
| math_mask_ratio | 1.8274e-05 | 6.69434e-06 | 4.48142e-11 | 1.05737e-05 | 1.73546e-05 | 2.59399e-05 | 2.68939e-05 |
| table_area_ratio | 0.0341333 | 0.0248091 | 0.000615492 | 0 | 0.0441694 | 0.0568243 | 0.0582304 |
| equation_area_ratio | 0.0584544 | 0.00416209 | 1.7323e-05 | 0.0548883 | 0.056182 | 0.0634818 | 0.0642929 |
| figure_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation_deg | 0.0135791 | 1.36175 | 1.85436 | -0.986761 | -0.911395 | 1.65386 | 1.93889 |

## Categorical diversity

| Field | Unique | Entropy bits | Top counts |
|---|---:|---:|---|
| layout_type | 1 | 0 | `{"double_col": 3}` |
| density_level | 1 | 0 | `{"sparse": 3}` |
| noise_level | 2 | 0.918296 | `{"clean": 2, "medium": 1}` |
| scale_profile | 1 | 0 | `{"dpi300": 3}` |
| page_family | 1 | 0 | `{"academic": 3}` |
| dominant_script | 2 | 0.918296 | `{"latin": 2, "unknown": 1}` |
| has_table | 2 | 0.918296 | `{"1": 2, "0": 1}` |
| has_equation | 1 | 0 | `{"1": 3}` |
| has_figure | 1 | 0 | `{"0": 3}` |
| fallback_used | 1 | 0 | `{"0": 3}` |

## Joint coverage

| Fields | Unique combinations | Entropy bits | Top combinations |
|---|---:|---:|---|
| layout_type × noise_level | 2 | 0.918296 | `{"double_col × clean": 2, "double_col × medium": 1}` |
| density_level × has_table | 2 | 0.918296 | `{"sparse × 1": 2, "sparse × 0": 1}` |
| density_level × has_equation | 1 | 0 | `{"sparse × 1": 3}` |
| layout_type × has_table | 2 | 0.918296 | `{"double_col × 1": 2, "double_col × 0": 1}` |
| has_table × has_equation | 2 | 0.918296 | `{"1 × 1": 2, "0 × 1": 1}` |
| dominant_script × has_equation | 2 | 0.918296 | `{"latin × 1": 2, "unknown × 1": 1}` |

## Target vs observed gap

### `layout_type`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `academic` | 0.1 | 0 | -0.1 | 0.1 |
| `double_col` | 0.26 | 1 | 0.74 | 0.74 |
| `mixed_cols` | 0.2 | 0 | -0.2 | 0.2 |
| `report_like` | 0.08 | 0 | -0.08 | 0.08 |
| `single_col` | 0.36 | 0 | -0.36 | 0.36 |

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
| `dpi200` | 0.22 | 0 | -0.22 | 0.22 |
| `dpi300` | 0.7 | 1 | 0.3 | 0.3 |
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
| info | math_mask_variance | math_mask_ratio variance is very low. | Increase LaTeX expression size, equation count, or formula layout variation. |
| info | layout_diversity | layout_type entropy is low: 0.000 bits. | Balance layout.layout_type_dist or add more page families. |
| info | target_vs_observed:layout_type | `double_col` is over-produced; signed gap=0.740. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `mixed_cols` is under-produced; signed gap=-0.200. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `single_col` is under-produced; signed gap=-0.360. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `dense` is under-produced; signed gap=-0.180. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `normal` is under-produced; signed gap=-0.500. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `sparse` is over-produced; signed gap=0.750. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi200` is under-produced; signed gap=-0.220. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi300` is over-produced; signed gap=0.300. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `a4_portrait` is under-produced; signed gap=-0.500. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `letter_portrait` is under-produced; signed gap=-0.180. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `unknown` is over-produced; signed gap=1.000. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
