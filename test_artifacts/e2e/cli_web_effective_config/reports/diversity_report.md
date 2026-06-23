# Diversity Report

- Created at: `2026-06-23T17:04:38+00:00`
- Page count: `1`

## Numeric variance summary

| Field | Mean | Std | Variance | Min | P50 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| line_count | 35 | 0 | 0 | 35 | 35 | 35 | 35 |
| block_count | 8 | 0 | 0 | 8 | 8 | 8 | 8 |
| math_line_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| equation_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text_mask_ratio | 0.00369572 | 0 | 0 | 0.00369572 | 0.00369572 | 0.00369572 | 0.00369572 |
| math_mask_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| equation_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation_deg | 1.85004 | 0 | 0 | 1.85004 | 1.85004 | 1.85004 | 1.85004 |

## Categorical diversity

| Field | Unique | Entropy bits | Top counts |
|---|---:|---:|---|
| layout_type | 1 | 0 | `{"single_col": 1}` |
| density_level | 1 | 0 | `{"sparse": 1}` |
| noise_level | 1 | 0 | `{"clean": 1}` |
| scale_profile | 1 | 0 | `{"dpi300": 1}` |
| page_family | 1 | 0 | `{"book": 1}` |
| dominant_script | 1 | 0 | `{"unknown": 1}` |
| has_table | 1 | 0 | `{"0": 1}` |
| has_equation | 1 | 0 | `{"0": 1}` |
| has_figure | 1 | 0 | `{"0": 1}` |
| fallback_used | 1 | 0 | `{"0": 1}` |

## Joint coverage

| Fields | Unique combinations | Entropy bits | Top combinations |
|---|---:|---:|---|
| layout_type × noise_level | 1 | 0 | `{"single_col × clean": 1}` |
| density_level × has_table | 1 | 0 | `{"sparse × 0": 1}` |
| density_level × has_equation | 1 | 0 | `{"sparse × 0": 1}` |
| layout_type × has_table | 1 | 0 | `{"single_col × 0": 1}` |
| has_table × has_equation | 1 | 0 | `{"0 × 0": 1}` |
| dominant_script × has_equation | 1 | 0 | `{"unknown × 0": 1}` |

## Target vs observed gap

### `layout_type`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `academic` | 0.1 | 0 | -0.1 | 0.1 |
| `double_col` | 0.26 | 0 | -0.26 | 0.26 |
| `mixed_cols` | 0.2 | 0 | -0.2 | 0.2 |
| `report_like` | 0.08 | 0 | -0.08 | 0.08 |
| `single_col` | 0.36 | 1 | 0.64 | 0.64 |

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
| `clean` | 0.55 | 1 | 0.45 | 0.45 |
| `heavy` | 0.1 | 0 | -0.1 | 0.1 |
| `medium` | 0.35 | 0 | -0.35 | 0.35 |

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
| warning | tables | Observed table page ratio is low: 0.000. | Increase content.has_table_prob and inspect table QC/layout failures. |
| info | latex | Observed equation page ratio is low: 0.000. | Increase content.has_equation_prob or equation block placement diversity. |
| info | math_mask_variance | math_mask_ratio variance is very low. | Increase LaTeX expression size, equation count, or formula layout variation. |
| info | layout_diversity | layout_type entropy is low: 0.000 bits. | Balance layout.layout_type_dist or add more page families. |
| info | script_diversity | dominant_script entropy is low: 0.000 bits. | Balance render.text.scripts_dist or add more multilingual content bank entries. |
| info | target_vs_observed:layout_type | `double_col` is under-produced; signed gap=-0.260. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `mixed_cols` is under-produced; signed gap=-0.200. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `single_col` is over-produced; signed gap=0.640. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `dense` is under-produced; signed gap=-0.180. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `normal` is under-produced; signed gap=-0.500. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `sparse` is over-produced; signed gap=0.750. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:noise_level | `clean` is over-produced; signed gap=0.450. | Adjust the config distribution for `noise_level` or inspect generation/QC constraints. |
| info | target_vs_observed:noise_level | `medium` is under-produced; signed gap=-0.350. | Adjust the config distribution for `noise_level` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi200` is under-produced; signed gap=-0.220. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi300` is over-produced; signed gap=0.300. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `a4_portrait` is under-produced; signed gap=-0.500. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `letter_portrait` is under-produced; signed gap=-0.180. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `unknown` is over-produced; signed gap=1.000. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
