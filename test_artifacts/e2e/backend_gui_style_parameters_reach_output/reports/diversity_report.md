# Diversity Report

- Created at: `2026-06-23T17:04:31+00:00`
- Page count: `4`

## Numeric variance summary

| Field | Mean | Std | Variance | Min | P50 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| line_count | 37.75 | 12.2755 | 150.688 | 21 | 37.5 | 52.9 | 55 |
| block_count | 7.75 | 0.829156 | 0.6875 | 7 | 7.5 | 8.85 | 9 |
| math_line_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| equation_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text_mask_ratio | 0.0054893 | 0.00561684 | 3.15488e-05 | 0.00047593 | 0.00329867 | 0.013336 | 0.0148839 |
| math_mask_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| equation_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation_deg | -0.390747 | 0.809087 | 0.654621 | -1.32153 | -0.501229 | 0.638849 | 0.761002 |

## Categorical diversity

| Field | Unique | Entropy bits | Top counts |
|---|---:|---:|---|
| layout_type | 2 | 0.811278 | `{"single_col": 3, "double_col": 1}` |
| density_level | 1 | 0 | `{"sparse": 4}` |
| noise_level | 2 | 1 | `{"medium": 2, "clean": 2}` |
| scale_profile | 2 | 1 | `{"dpi300": 2, "dpi200": 2}` |
| page_family | 3 | 1.5 | `{"book": 2, "notes": 1, "worksheet": 1}` |
| dominant_script | 1 | 0 | `{"unknown": 4}` |
| has_table | 1 | 0 | `{"0": 4}` |
| has_equation | 1 | 0 | `{"0": 4}` |
| has_figure | 1 | 0 | `{"0": 4}` |
| fallback_used | 1 | 0 | `{"0": 4}` |

## Joint coverage

| Fields | Unique combinations | Entropy bits | Top combinations |
|---|---:|---:|---|
| layout_type × noise_level | 3 | 1.5 | `{"single_col × medium": 2, "single_col × clean": 1, "double_col × clean": 1}` |
| density_level × has_table | 1 | 0 | `{"sparse × 0": 4}` |
| density_level × has_equation | 1 | 0 | `{"sparse × 0": 4}` |
| layout_type × has_table | 2 | 0.811278 | `{"single_col × 0": 3, "double_col × 0": 1}` |
| has_table × has_equation | 1 | 0 | `{"0 × 0": 4}` |
| dominant_script × has_equation | 1 | 0 | `{"unknown × 0": 4}` |

## Target vs observed gap

### `layout_type`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `academic` | 0.1 | 0 | -0.1 | 0.1 |
| `double_col` | 0.26 | 0.25 | -0.01 | 0.01 |
| `mixed_cols` | 0.2 | 0 | -0.2 | 0.2 |
| `report_like` | 0.08 | 0 | -0.08 | 0.08 |
| `single_col` | 0.36 | 0.75 | 0.39 | 0.39 |

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
| `clean` | 0.55 | 0.5 | -0.05 | 0.05 |
| `heavy` | 0.1 | 0 | -0.1 | 0.1 |
| `medium` | 0.35 | 0.5 | 0.15 | 0.15 |

### `scale_profile`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `dpi200` | 0.22 | 0.5 | 0.28 | 0.28 |
| `dpi300` | 0.7 | 0.5 | -0.2 | 0.2 |
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
| info | script_diversity | dominant_script entropy is low: 0.000 bits. | Balance render.text.scripts_dist or add more multilingual content bank entries. |
| info | target_vs_observed:layout_type | `mixed_cols` is under-produced; signed gap=-0.200. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `single_col` is over-produced; signed gap=0.390. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `dense` is under-produced; signed gap=-0.180. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `normal` is under-produced; signed gap=-0.500. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `sparse` is over-produced; signed gap=0.750. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:noise_level | `medium` is over-produced; signed gap=0.150. | Adjust the config distribution for `noise_level` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi200` is over-produced; signed gap=0.280. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi300` is under-produced; signed gap=-0.200. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `a4_portrait` is under-produced; signed gap=-0.500. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `letter_portrait` is under-produced; signed gap=-0.180. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `unknown` is over-produced; signed gap=1.000. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
