# Diversity Report

- Created at: `2026-06-23T16:57:56+00:00`
- Page count: `3`

## Numeric variance summary

| Field | Mean | Std | Variance | Min | P50 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| line_count | 32 | 16.6733 | 278 | 9 | 39 | 47.1 | 48 |
| block_count | 5.33333 | 1.24722 | 1.55556 | 4 | 5 | 6.8 | 7 |
| math_line_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_block_count | 0.333333 | 0.471405 | 0.222222 | 0 | 0 | 0.9 | 1 |
| equation_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text_mask_ratio | 0.0122389 | 0.0145104 | 0.000210551 | 0.0011803 | 0.002798 | 0.0297443 | 0.0327384 |
| math_mask_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| table_area_ratio | 0.0405778 | 0.0573856 | 0.00329311 | 0 | 0 | 0.10956 | 0.121733 |
| equation_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| figure_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation_deg | 0.0390619 | 1.30692 | 1.70804 | -1.63499 | 0.197697 | 1.4188 | 1.55448 |

## Categorical diversity

| Field | Unique | Entropy bits | Top counts |
|---|---:|---:|---|
| layout_type | 1 | 0 | `{"single_col": 3}` |
| density_level | 2 | 0.918296 | `{"sparse": 2, "mixed": 1}` |
| noise_level | 1 | 0 | `{"clean": 3}` |
| scale_profile | 2 | 0.918296 | `{"dpi300": 2, "dpi200": 1}` |
| page_family | 3 | 1.58496 | `{"book": 1, "report": 1, "notes": 1}` |
| dominant_script | 1 | 0 | `{"latin": 3}` |
| has_table | 2 | 0.918296 | `{"0": 2, "1": 1}` |
| has_equation | 1 | 0 | `{"0": 3}` |
| has_figure | 1 | 0 | `{"0": 3}` |
| fallback_used | 1 | 0 | `{"0": 3}` |

## Joint coverage

| Fields | Unique combinations | Entropy bits | Top combinations |
|---|---:|---:|---|
| layout_type × noise_level | 1 | 0 | `{"single_col × clean": 3}` |
| density_level × has_table | 3 | 1.58496 | `{"sparse × 1": 1, "mixed × 0": 1, "sparse × 0": 1}` |
| density_level × has_equation | 2 | 0.918296 | `{"sparse × 0": 2, "mixed × 0": 1}` |
| layout_type × has_table | 2 | 0.918296 | `{"single_col × 0": 2, "single_col × 1": 1}` |
| has_table × has_equation | 2 | 0.918296 | `{"0 × 0": 2, "1 × 0": 1}` |
| dominant_script × has_equation | 1 | 0 | `{"latin × 0": 3}` |

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
| `mixed` | 0.07 | 0.333333 | 0.263333 | 0.263333 |
| `normal` | 0.5 | 0 | -0.5 | 0.5 |
| `sparse` | 0.25 | 0.666667 | 0.416667 | 0.416667 |

### `noise_level`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `clean` | 0.55 | 1 | 0.45 | 0.45 |
| `heavy` | 0.1 | 0 | -0.1 | 0.1 |
| `medium` | 0.35 | 0 | -0.35 | 0.35 |

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
| info | latex | Observed equation page ratio is low: 0.000. | Increase content.has_equation_prob or equation block placement diversity. |
| info | math_mask_variance | math_mask_ratio variance is very low. | Increase LaTeX expression size, equation count, or formula layout variation. |
| info | layout_diversity | layout_type entropy is low: 0.000 bits. | Balance layout.layout_type_dist or add more page families. |
| info | script_diversity | dominant_script entropy is low: 0.000 bits. | Balance render.text.scripts_dist or add more multilingual content bank entries. |
| info | target_vs_observed:layout_type | `double_col` is under-produced; signed gap=-0.260. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `mixed_cols` is under-produced; signed gap=-0.200. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `single_col` is over-produced; signed gap=0.640. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `dense` is under-produced; signed gap=-0.180. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `mixed` is over-produced; signed gap=0.263. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `normal` is under-produced; signed gap=-0.500. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `sparse` is over-produced; signed gap=0.417. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:noise_level | `clean` is over-produced; signed gap=0.450. | Adjust the config distribution for `noise_level` or inspect generation/QC constraints. |
| info | target_vs_observed:noise_level | `medium` is under-produced; signed gap=-0.350. | Adjust the config distribution for `noise_level` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `a4_portrait` is under-produced; signed gap=-0.500. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `letter_portrait` is under-produced; signed gap=-0.180. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `unknown` is over-produced; signed gap=1.000. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
