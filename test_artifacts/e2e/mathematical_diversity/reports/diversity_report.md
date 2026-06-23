# Diversity Report

- Created at: `2026-06-23T17:28:45+00:00`
- Page count: `30`

## Numeric variance summary

| Field | Mean | Std | Variance | Min | P50 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| line_count | 64.6333 | 32.1211 | 1031.77 | 9 | 68 | 122.95 | 144 |
| block_count | 6.56667 | 2.31924 | 5.37889 | 2 | 7 | 10 | 11 |
| math_line_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_block_count | 1.66667 | 1.07497 | 1.15556 | 0 | 1 | 3 | 4 |
| equation_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text_mask_ratio | 0.00632561 | 0.00371576 | 1.38069e-05 | 0.00043421 | 0.00610629 | 0.0124962 | 0.0147332 |
| math_mask_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_area_ratio | 0.168855 | 0.11349 | 0.0128799 | 0 | 0.167044 | 0.410573 | 0.439346 |
| equation_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation_deg | -0.0820964 | 1.22966 | 1.51207 | -1.99586 | -0.00867751 | 1.80216 | 1.90715 |

## Categorical diversity

| Field | Unique | Entropy bits | Top counts |
|---|---:|---:|---|
| layout_type | 3 | 1.3681 | `{"double_col": 14, "single_col": 13, "mixed_cols": 3}` |
| density_level | 2 | 0.210842 | `{"sparse": 29, "normal": 1}` |
| noise_level | 3 | 1.3681 | `{"clean": 14, "medium": 13, "heavy": 3}` |
| scale_profile | 3 | 1.23096 | `{"dpi300": 18, "dpi200": 10, "lowres_capture": 2}` |
| page_family | 5 | 2.13306 | `{"book": 11, "report": 7, "academic": 6, "notes": 4, "worksheet": 2}` |
| dominant_script | 2 | 0.353359 | `{"latin": 28, "unknown": 2}` |
| has_table | 2 | 0.468996 | `{"1": 27, "0": 3}` |
| has_equation | 1 | 0 | `{"0": 30}` |
| has_figure | 1 | 0 | `{"0": 30}` |
| fallback_used | 1 | 0 | `{"0": 30}` |

## Joint coverage

| Fields | Unique combinations | Entropy bits | Top combinations |
|---|---:|---:|---|
| layout_type × noise_level | 9 | 2.65324 | `{"double_col × medium": 8, "single_col × clean": 8, "double_col × clean": 5, "single_col × medium": 4, "mixed_cols × medium": 1, "mixed_cols × heavy": 1, "mixed_cols × clean": 1, "single_col × heavy": 1, "double_col × heavy": 1}` |
| density_level × has_table | 3 | 0.67468 | `{"sparse × 1": 26, "sparse × 0": 3, "normal × 1": 1}` |
| density_level × has_equation | 2 | 0.210842 | `{"sparse × 0": 29, "normal × 0": 1}` |
| layout_type × has_table | 4 | 1.70582 | `{"double_col × 1": 14, "single_col × 1": 10, "mixed_cols × 1": 3, "single_col × 0": 3}` |
| has_table × has_equation | 2 | 0.468996 | `{"1 × 0": 27, "0 × 0": 3}` |
| dominant_script × has_equation | 2 | 0.353359 | `{"latin × 0": 28, "unknown × 0": 2}` |

## Target vs observed gap

### `layout_type`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `academic` | 0.1 | 0 | -0.1 | 0.1 |
| `double_col` | 0.26 | 0.466667 | 0.206667 | 0.206667 |
| `mixed_cols` | 0.2 | 0.1 | -0.1 | 0.1 |
| `report_like` | 0.08 | 0 | -0.08 | 0.08 |
| `single_col` | 0.36 | 0.433333 | 0.0733333 | 0.0733333 |

### `density_level`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `dense` | 0.18 | 0 | -0.18 | 0.18 |
| `mixed` | 0.07 | 0 | -0.07 | 0.07 |
| `normal` | 0.5 | 0.0333333 | -0.466667 | 0.466667 |
| `sparse` | 0.25 | 0.966667 | 0.716667 | 0.716667 |

### `noise_level`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `clean` | 0.55 | 0.466667 | -0.0833333 | 0.0833333 |
| `heavy` | 0.1 | 0.1 | 0 | 0 |
| `medium` | 0.35 | 0.433333 | 0.0833333 | 0.0833333 |

### `scale_profile`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `dpi200` | 0.22 | 0.333333 | 0.113333 | 0.113333 |
| `dpi300` | 0.7 | 0.6 | -0.1 | 0.1 |
| `hires_crop` | 0.02 | 0 | -0.02 | 0.02 |
| `lowres_capture` | 0.06 | 0.0666667 | 0.00666667 | 0.00666667 |

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
| info | latex | Observed equation page ratio is low: 0.000. | Increase content.has_equation_prob or equation block placement diversity. |
| info | math_mask_variance | math_mask_ratio variance is very low. | Increase LaTeX expression size, equation count, or formula layout variation. |
| info | script_diversity | dominant_script entropy is low: 0.353 bits. | Balance render.text.scripts_dist or add more multilingual content bank entries. |
| info | target_vs_observed:layout_type | `double_col` is over-produced; signed gap=0.207. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `dense` is under-produced; signed gap=-0.180. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `normal` is under-produced; signed gap=-0.467. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `sparse` is over-produced; signed gap=0.717. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `a4_portrait` is under-produced; signed gap=-0.500. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `letter_portrait` is under-produced; signed gap=-0.180. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `unknown` is over-produced; signed gap=1.000. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
