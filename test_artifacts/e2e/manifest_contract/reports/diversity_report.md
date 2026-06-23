# Diversity Report

- Created at: `2026-06-23T16:58:29+00:00`
- Page count: `2`

## Numeric variance summary

| Field | Mean | Std | Variance | Min | P50 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| line_count | 51 | 7 | 49 | 44 | 51 | 57.3 | 58 |
| block_count | 7.5 | 0.5 | 0.25 | 7 | 7.5 | 7.95 | 8 |
| math_line_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_block_count | 1 | 1 | 1 | 0 | 1 | 1.9 | 2 |
| equation_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text_mask_ratio | 0.00570137 | 0.00354426 | 1.25618e-05 | 0.0021571 | 0.00570137 | 0.0088912 | 0.00924563 |
| math_mask_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_area_ratio | 0.139014 | 0.139014 | 0.019325 | 0 | 0.139014 | 0.264127 | 0.278029 |
| equation_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation_deg | -0.195878 | 1.79427 | 3.21941 | -1.99015 | -0.195878 | 1.41897 | 1.59839 |

## Categorical diversity

| Field | Unique | Entropy bits | Top counts |
|---|---:|---:|---|
| layout_type | 2 | 1 | `{"mixed_cols": 1, "single_col": 1}` |
| density_level | 1 | 0 | `{"sparse": 2}` |
| noise_level | 1 | 0 | `{"medium": 2}` |
| scale_profile | 1 | 0 | `{"dpi300": 2}` |
| page_family | 2 | 1 | `{"book": 1, "worksheet": 1}` |
| dominant_script | 1 | 0 | `{"latin": 2}` |
| has_table | 2 | 1 | `{"0": 1, "1": 1}` |
| has_equation | 1 | 0 | `{"0": 2}` |
| has_figure | 1 | 0 | `{"0": 2}` |
| fallback_used | 1 | 0 | `{"0": 2}` |

## Joint coverage

| Fields | Unique combinations | Entropy bits | Top combinations |
|---|---:|---:|---|
| layout_type × noise_level | 2 | 1 | `{"mixed_cols × medium": 1, "single_col × medium": 1}` |
| density_level × has_table | 2 | 1 | `{"sparse × 0": 1, "sparse × 1": 1}` |
| density_level × has_equation | 1 | 0 | `{"sparse × 0": 2}` |
| layout_type × has_table | 2 | 1 | `{"mixed_cols × 0": 1, "single_col × 1": 1}` |
| has_table × has_equation | 2 | 1 | `{"0 × 0": 1, "1 × 0": 1}` |
| dominant_script × has_equation | 1 | 0 | `{"latin × 0": 2}` |

## Target vs observed gap

### `layout_type`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `academic` | 0.1 | 0 | -0.1 | 0.1 |
| `double_col` | 0.26 | 0 | -0.26 | 0.26 |
| `mixed_cols` | 0.2 | 0.5 | 0.3 | 0.3 |
| `report_like` | 0.08 | 0 | -0.08 | 0.08 |
| `single_col` | 0.36 | 0.5 | 0.14 | 0.14 |

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
| `clean` | 0.55 | 0 | -0.55 | 0.55 |
| `heavy` | 0.1 | 0 | -0.1 | 0.1 |
| `medium` | 0.35 | 1 | 0.65 | 0.65 |

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
| info | latex | Observed equation page ratio is low: 0.000. | Increase content.has_equation_prob or equation block placement diversity. |
| info | math_mask_variance | math_mask_ratio variance is very low. | Increase LaTeX expression size, equation count, or formula layout variation. |
| info | script_diversity | dominant_script entropy is low: 0.000 bits. | Balance render.text.scripts_dist or add more multilingual content bank entries. |
| info | target_vs_observed:layout_type | `double_col` is under-produced; signed gap=-0.260. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `mixed_cols` is over-produced; signed gap=0.300. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `dense` is under-produced; signed gap=-0.180. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `normal` is under-produced; signed gap=-0.500. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `sparse` is over-produced; signed gap=0.750. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:noise_level | `clean` is under-produced; signed gap=-0.550. | Adjust the config distribution for `noise_level` or inspect generation/QC constraints. |
| info | target_vs_observed:noise_level | `medium` is over-produced; signed gap=0.650. | Adjust the config distribution for `noise_level` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi200` is under-produced; signed gap=-0.220. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi300` is over-produced; signed gap=0.300. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `a4_portrait` is under-produced; signed gap=-0.500. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `letter_portrait` is under-produced; signed gap=-0.180. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `unknown` is over-produced; signed gap=1.000. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
