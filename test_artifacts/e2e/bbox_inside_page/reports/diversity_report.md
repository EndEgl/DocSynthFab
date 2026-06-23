# Diversity Report

- Created at: `2026-06-23T16:58:52+00:00`
- Page count: `3`

## Numeric variance summary

| Field | Mean | Std | Variance | Min | P50 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| line_count | 72.6667 | 35.5184 | 1261.56 | 29 | 73 | 111.7 | 116 |
| block_count | 5.66667 | 2.35702 | 5.55556 | 4 | 4 | 8.5 | 9 |
| math_line_count | 0.666667 | 0.471405 | 0.222222 | 0 | 1 | 1 | 1 |
| table_block_count | 2 | 0.816497 | 0.666667 | 1 | 2 | 2.9 | 3 |
| equation_block_count | 1 | 0.816497 | 0.666667 | 0 | 1 | 1.9 | 2 |
| figure_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text_mask_ratio | 0.00377257 | 0.002252 | 5.07152e-06 | 0.00129332 | 0.00328093 | 0.0063972 | 0.00674346 |
| math_mask_ratio | 4.87022e-06 | 4.54226e-06 | 2.06322e-11 | 0 | 3.67779e-06 | 1.02074e-05 | 1.09329e-05 |
| table_area_ratio | 0.198173 | 0.0561435 | 0.0031521 | 0.146894 | 0.171316 | 0.265811 | 0.27631 |
| equation_area_ratio | 0.0232621 | 0.0165086 | 0.000272534 | 0 | 0.0331732 | 0.036269 | 0.036613 |
| figure_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation_deg | -1.55352 | 0.481047 | 0.231406 | -1.95157 | -1.83228 | -0.972271 | -0.876714 |

## Categorical diversity

| Field | Unique | Entropy bits | Top counts |
|---|---:|---:|---|
| layout_type | 2 | 0.918296 | `{"double_col": 2, "single_col": 1}` |
| density_level | 1 | 0 | `{"sparse": 3}` |
| noise_level | 3 | 1.58496 | `{"heavy": 1, "clean": 1, "medium": 1}` |
| scale_profile | 1 | 0 | `{"dpi300": 3}` |
| page_family | 2 | 0.918296 | `{"report": 2, "book": 1}` |
| dominant_script | 1 | 0 | `{"latin": 3}` |
| has_table | 1 | 0 | `{"1": 3}` |
| has_equation | 2 | 0.918296 | `{"1": 2, "0": 1}` |
| has_figure | 1 | 0 | `{"0": 3}` |
| fallback_used | 1 | 0 | `{"0": 3}` |

## Joint coverage

| Fields | Unique combinations | Entropy bits | Top combinations |
|---|---:|---:|---|
| layout_type × noise_level | 3 | 1.58496 | `{"single_col × heavy": 1, "double_col × clean": 1, "double_col × medium": 1}` |
| density_level × has_table | 1 | 0 | `{"sparse × 1": 3}` |
| density_level × has_equation | 2 | 0.918296 | `{"sparse × 1": 2, "sparse × 0": 1}` |
| layout_type × has_table | 2 | 0.918296 | `{"double_col × 1": 2, "single_col × 1": 1}` |
| has_table × has_equation | 2 | 0.918296 | `{"1 × 1": 2, "1 × 0": 1}` |
| dominant_script × has_equation | 2 | 0.918296 | `{"latin × 1": 2, "latin × 0": 1}` |

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
| `clean` | 0.55 | 0.333333 | -0.216667 | 0.216667 |
| `heavy` | 0.1 | 0.333333 | 0.233333 | 0.233333 |
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
| info | script_diversity | dominant_script entropy is low: 0.000 bits. | Balance render.text.scripts_dist or add more multilingual content bank entries. |
| info | target_vs_observed:layout_type | `double_col` is over-produced; signed gap=0.407. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `mixed_cols` is under-produced; signed gap=-0.200. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `dense` is under-produced; signed gap=-0.180. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `normal` is under-produced; signed gap=-0.500. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `sparse` is over-produced; signed gap=0.750. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:noise_level | `clean` is under-produced; signed gap=-0.217. | Adjust the config distribution for `noise_level` or inspect generation/QC constraints. |
| info | target_vs_observed:noise_level | `heavy` is over-produced; signed gap=0.233. | Adjust the config distribution for `noise_level` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi200` is under-produced; signed gap=-0.220. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi300` is over-produced; signed gap=0.300. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `a4_portrait` is under-produced; signed gap=-0.500. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `letter_portrait` is under-produced; signed gap=-0.180. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `unknown` is over-produced; signed gap=1.000. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
