# Diversity Report

- Created at: `2026-06-23T16:58:37+00:00`
- Page count: `3`

## Numeric variance summary

| Field | Mean | Std | Variance | Min | P50 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| line_count | 33.6667 | 4.49691 | 20.2222 | 30 | 31 | 39.1 | 40 |
| block_count | 3.33333 | 1.24722 | 1.55556 | 2 | 3 | 4.8 | 5 |
| math_line_count | 0.333333 | 0.471405 | 0.222222 | 0 | 0 | 0.9 | 1 |
| table_block_count | 1 | 0 | 0 | 1 | 1 | 1 | 1 |
| equation_block_count | 0.666667 | 0.471405 | 0.222222 | 0 | 1 | 1 | 1 |
| figure_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text_mask_ratio | 0.00383648 | 0.00326069 | 1.06321e-05 | 0.00102737 | 0.00207405 | 0.00777462 | 0.00840802 |
| math_mask_ratio | 1.22593e-06 | 1.73373e-06 | 3.00582e-12 | 0 | 0 | 3.31001e-06 | 3.67779e-06 |
| table_area_ratio | 0.136733 | 0.0148332 | 0.000220024 | 0.11579 | 0.146175 | 0.148029 | 0.148235 |
| equation_area_ratio | 0.0479355 | 0.0652465 | 0.00425711 | 0 | 0.00362219 | 0.126528 | 0.140184 |
| figure_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation_deg | -1.60332 | 0.189463 | 0.0358963 | -1.84237 | -1.5886 | -1.39994 | -1.37898 |

## Categorical diversity

| Field | Unique | Entropy bits | Top counts |
|---|---:|---:|---|
| layout_type | 2 | 0.918296 | `{"mixed_cols": 2, "double_col": 1}` |
| density_level | 1 | 0 | `{"sparse": 3}` |
| noise_level | 1 | 0 | `{"clean": 3}` |
| scale_profile | 3 | 1.58496 | `{"lowres_capture": 1, "dpi300": 1, "dpi200": 1}` |
| page_family | 2 | 0.918296 | `{"notes": 2, "academic": 1}` |
| dominant_script | 2 | 0.918296 | `{"latin": 2, "unknown": 1}` |
| has_table | 1 | 0 | `{"1": 3}` |
| has_equation | 2 | 0.918296 | `{"0": 2, "1": 1}` |
| has_figure | 1 | 0 | `{"0": 3}` |
| fallback_used | 1 | 0 | `{"0": 3}` |

## Joint coverage

| Fields | Unique combinations | Entropy bits | Top combinations |
|---|---:|---:|---|
| layout_type × noise_level | 2 | 0.918296 | `{"mixed_cols × clean": 2, "double_col × clean": 1}` |
| density_level × has_table | 1 | 0 | `{"sparse × 1": 3}` |
| density_level × has_equation | 2 | 0.918296 | `{"sparse × 0": 2, "sparse × 1": 1}` |
| layout_type × has_table | 2 | 0.918296 | `{"mixed_cols × 1": 2, "double_col × 1": 1}` |
| has_table × has_equation | 2 | 0.918296 | `{"1 × 0": 2, "1 × 1": 1}` |
| dominant_script × has_equation | 2 | 0.918296 | `{"latin × 0": 2, "unknown × 1": 1}` |

## Target vs observed gap

### `layout_type`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `academic` | 0.1 | 0 | -0.1 | 0.1 |
| `double_col` | 0.26 | 0.333333 | 0.0733333 | 0.0733333 |
| `mixed_cols` | 0.2 | 0.666667 | 0.466667 | 0.466667 |
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
| `clean` | 0.55 | 1 | 0.45 | 0.45 |
| `heavy` | 0.1 | 0 | -0.1 | 0.1 |
| `medium` | 0.35 | 0 | -0.35 | 0.35 |

### `scale_profile`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `dpi200` | 0.22 | 0.333333 | 0.113333 | 0.113333 |
| `dpi300` | 0.7 | 0.333333 | -0.366667 | 0.366667 |
| `hires_crop` | 0.02 | 0 | -0.02 | 0.02 |
| `lowres_capture` | 0.06 | 0.333333 | 0.273333 | 0.273333 |

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
| info | target_vs_observed:layout_type | `mixed_cols` is over-produced; signed gap=0.467. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:layout_type | `single_col` is under-produced; signed gap=-0.360. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `dense` is under-produced; signed gap=-0.180. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `normal` is under-produced; signed gap=-0.500. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `sparse` is over-produced; signed gap=0.750. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:noise_level | `clean` is over-produced; signed gap=0.450. | Adjust the config distribution for `noise_level` or inspect generation/QC constraints. |
| info | target_vs_observed:noise_level | `medium` is under-produced; signed gap=-0.350. | Adjust the config distribution for `noise_level` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `dpi300` is under-produced; signed gap=-0.367. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:scale_profile | `lowres_capture` is over-produced; signed gap=0.273. | Adjust the config distribution for `scale_profile` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `a4_portrait` is under-produced; signed gap=-0.500. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `letter_portrait` is under-produced; signed gap=-0.180. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `unknown` is over-produced; signed gap=1.000. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
