# Diversity Report

- Created at: `2026-06-23T17:02:46+00:00`
- Page count: `3`

## Numeric variance summary

| Field | Mean | Std | Variance | Min | P50 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| line_count | 36.3333 | 12.6842 | 160.889 | 19 | 41 | 48.2 | 49 |
| block_count | 4 | 0.816497 | 0.666667 | 3 | 4 | 4.9 | 5 |
| math_line_count | 0.666667 | 0.471405 | 0.222222 | 0 | 1 | 1 | 1 |
| table_block_count | 0.666667 | 0.471405 | 0.222222 | 0 | 1 | 1 | 1 |
| equation_block_count | 0.666667 | 0.471405 | 0.222222 | 0 | 1 | 1 | 1 |
| figure_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text_mask_ratio | 0.00434823 | 0.000301257 | 9.07556e-08 | 0.00404971 | 0.00423423 | 0.00470808 | 0.00476073 |
| math_mask_ratio | 9.48181e-06 | 6.70465e-06 | 4.49524e-11 | 0 | 1.42227e-05 | 1.42227e-05 | 1.42227e-05 |
| table_area_ratio | 0.0671926 | 0.0493932 | 0.00243968 | 0 | 0.0842544 | 0.114017 | 0.117323 |
| equation_area_ratio | 0.0548276 | 0.0409379 | 0.00167591 | 0 | 0.0661382 | 0.095124 | 0.0983447 |
| figure_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation_deg | -0.333483 | 1.1339 | 1.28572 | -1.62849 | -0.505003 | 0.969239 | 1.13304 |

## Categorical diversity

| Field | Unique | Entropy bits | Top counts |
|---|---:|---:|---|
| layout_type | 2 | 0.918296 | `{"single_col": 2, "double_col": 1}` |
| density_level | 1 | 0 | `{"sparse": 3}` |
| noise_level | 2 | 0.918296 | `{"clean": 2, "medium": 1}` |
| scale_profile | 2 | 0.918296 | `{"dpi200": 2, "hires_crop": 1}` |
| page_family | 2 | 0.918296 | `{"book": 2, "academic": 1}` |
| dominant_script | 1 | 0 | `{"latin": 3}` |
| has_table | 2 | 0.918296 | `{"1": 2, "0": 1}` |
| has_equation | 2 | 0.918296 | `{"1": 2, "0": 1}` |
| has_figure | 1 | 0 | `{"0": 3}` |
| fallback_used | 1 | 0 | `{"0": 3}` |

## Joint coverage

| Fields | Unique combinations | Entropy bits | Top combinations |
|---|---:|---:|---|
| layout_type × noise_level | 2 | 0.918296 | `{"single_col × clean": 2, "double_col × medium": 1}` |
| density_level × has_table | 2 | 0.918296 | `{"sparse × 1": 2, "sparse × 0": 1}` |
| density_level × has_equation | 2 | 0.918296 | `{"sparse × 1": 2, "sparse × 0": 1}` |
| layout_type × has_table | 2 | 0.918296 | `{"single_col × 1": 2, "double_col × 0": 1}` |
| has_table × has_equation | 2 | 0.918296 | `{"1 × 1": 2, "0 × 0": 1}` |
| dominant_script × has_equation | 2 | 0.918296 | `{"latin × 1": 2, "latin × 0": 1}` |

## Target vs observed gap

### `layout_type`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `academic` | 0.1 | 0 | -0.1 | 0.1 |
| `double_col` | 0.26 | 0.333333 | 0.0733333 | 0.0733333 |
| `mixed_cols` | 0.2 | 0 | -0.2 | 0.2 |
| `report_like` | 0.08 | 0 | -0.08 | 0.08 |
| `single_col` | 0.36 | 0.666667 | 0.306667 | 0.306667 |

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
| `dpi200` | 0.22 | 0.666667 | 0.446667 | 0.446667 |
| `dpi300` | 0.7 | 0 | -0.7 | 0.7 |
| `hires_crop` | 0.02 | 0.333333 | 0.313333 | 0.313333 |
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
| info | script_diversity | dominant_script entropy is low: 0.000 bits. | Balance render.text.scripts_dist or add more multilingual content bank entries. |
| info | target_vs_observed:layout_type | `mixed_cols` is under-produced; signed gap=-0.200. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `single_col` is over-produced; signed gap=0.307. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `dense` is under-produced; signed gap=-0.180. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `normal` is under-produced; signed gap=-0.500. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `sparse` is over-produced; signed gap=0.750. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi200` is over-produced; signed gap=0.447. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi300` is under-produced; signed gap=-0.700. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `hires_crop` is over-produced; signed gap=0.313. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `a4_portrait` is under-produced; signed gap=-0.500. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `letter_portrait` is under-produced; signed gap=-0.180. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `unknown` is over-produced; signed gap=1.000. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
