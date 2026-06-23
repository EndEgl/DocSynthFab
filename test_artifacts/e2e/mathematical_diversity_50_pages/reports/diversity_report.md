# Diversity Report

- Created at: `2026-06-23T17:04:15+00:00`
- Page count: `50`

## Numeric variance summary

| Field | Mean | Std | Variance | Min | P50 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| line_count | 59 | 27.8733 | 776.92 | 9 | 57 | 99.65 | 121 |
| block_count | 6.92 | 2.95188 | 8.7136 | 2 | 7 | 11.55 | 14 |
| math_line_count | 1.98 | 4.08162 | 16.6596 | 0 | 1 | 10.95 | 20 |
| table_block_count | 1.32 | 0.835225 | 0.6976 | 0 | 1 | 3 | 3 |
| equation_block_count | 1.16 | 0.578273 | 0.3344 | 0 | 1 | 2 | 4 |
| figure_block_count | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| text_mask_ratio | 0.00513656 | 0.00323081 | 1.04381e-05 | 0.000668806 | 0.0045942 | 0.0113272 | 0.0143236 |
| math_mask_ratio | 1.68298e-05 | 3.91085e-05 | 1.52947e-09 | 0 | 5.36539e-06 | 8.28725e-05 | 0.000240493 |
| table_area_ratio | 0.135903 | 0.0991136 | 0.00982352 | 0 | 0.13373 | 0.282833 | 0.471059 |
| equation_area_ratio | 0.0583632 | 0.0616876 | 0.00380535 | 0 | 0.0423003 | 0.165545 | 0.258514 |
| figure_area_ratio | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation_deg | 0.142585 | 1.1763 | 1.38369 | -1.99586 | 0.235131 | 1.8177 | 1.911 |

## Categorical diversity

| Field | Unique | Entropy bits | Top counts |
|---|---:|---:|---|
| layout_type | 3 | 1.32092 | `{"single_col": 24, "double_col": 22, "mixed_cols": 4}` |
| density_level | 2 | 0.141441 | `{"sparse": 49, "mixed": 1}` |
| noise_level | 3 | 1.35933 | `{"clean": 30, "medium": 12, "heavy": 8}` |
| scale_profile | 4 | 1.32129 | `{"dpi300": 33, "dpi200": 11, "lowres_capture": 5, "hires_crop": 1}` |
| page_family | 5 | 2.23327 | `{"book": 16, "report": 12, "worksheet": 8, "academic": 8, "notes": 6}` |
| dominant_script | 3 | 0.770664 | `{"latin": 41, "unknown": 8, "ru": 1}` |
| has_table | 2 | 0.584239 | `{"1": 43, "0": 7}` |
| has_equation | 2 | 0.924819 | `{"1": 33, "0": 17}` |
| has_figure | 1 | 0 | `{"0": 50}` |
| fallback_used | 1 | 0 | `{"0": 50}` |

## Joint coverage

| Fields | Unique combinations | Entropy bits | Top combinations |
|---|---:|---:|---|
| layout_type × noise_level | 8 | 2.61909 | `{"single_col × clean": 15, "double_col × clean": 13, "single_col × medium": 6, "double_col × medium": 6, "single_col × heavy": 3, "double_col × heavy": 3, "mixed_cols × heavy": 2, "mixed_cols × clean": 2}` |
| density_level × has_table | 3 | 0.667073 | `{"sparse × 1": 43, "sparse × 0": 6, "mixed × 0": 1}` |
| density_level × has_equation | 3 | 1.05412 | `{"sparse × 1": 32, "sparse × 0": 17, "mixed × 1": 1}` |
| layout_type × has_table | 5 | 1.82771 | `{"double_col × 1": 21, "single_col × 1": 18, "single_col × 0": 6, "mixed_cols × 1": 4, "double_col × 0": 1}` |
| has_table × has_equation | 4 | 1.48602 | `{"1 × 1": 27, "1 × 0": 16, "0 × 1": 6, "0 × 0": 1}` |
| dominant_script × has_equation | 5 | 1.6489 | `{"latin × 1": 25, "latin × 0": 16, "unknown × 1": 7, "unknown × 0": 1, "ru × 1": 1}` |

## Target vs observed gap

### `layout_type`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `academic` | 0.1 | 0 | -0.1 | 0.1 |
| `double_col` | 0.26 | 0.44 | 0.18 | 0.18 |
| `mixed_cols` | 0.2 | 0.08 | -0.12 | 0.12 |
| `report_like` | 0.08 | 0 | -0.08 | 0.08 |
| `single_col` | 0.36 | 0.48 | 0.12 | 0.12 |

### `density_level`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `dense` | 0.18 | 0 | -0.18 | 0.18 |
| `mixed` | 0.07 | 0.02 | -0.05 | 0.05 |
| `normal` | 0.5 | 0 | -0.5 | 0.5 |
| `sparse` | 0.25 | 0.98 | 0.73 | 0.73 |

### `noise_level`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `clean` | 0.55 | 0.6 | 0.05 | 0.05 |
| `heavy` | 0.1 | 0.16 | 0.06 | 0.06 |
| `medium` | 0.35 | 0.24 | -0.11 | 0.11 |

### `scale_profile`

| Value | Target | Observed | Signed gap | Abs gap |
|---|---:|---:|---:|---:|
| `dpi200` | 0.22 | 0.22 | 0 | 0 |
| `dpi300` | 0.7 | 0.66 | -0.04 | 0.04 |
| `hires_crop` | 0.02 | 0.02 | 0 | 0 |
| `lowres_capture` | 0.06 | 0.1 | 0.04 | 0.04 |

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
| info | script_diversity | dominant_script entropy is low: 0.771 bits. | Balance render.text.scripts_dist or add more multilingual content bank entries. |
| info | target_vs_observed:layout_type | `double_col` is over-produced; signed gap=0.180. | Adjust the config distribution for `layout_type` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `dense` is under-produced; signed gap=-0.180. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `normal` is under-produced; signed gap=-0.500. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:density_level | `sparse` is over-produced; signed gap=0.730. | Adjust the config distribution for `density_level` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `a4_portrait` is under-produced; signed gap=-0.500. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `letter_portrait` is under-produced; signed gap=-0.180. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
| info | target_vs_observed:page_size_name | `unknown` is over-produced; signed gap=1.000. | Adjust the config distribution for `page_size_name` or inspect generation/QC constraints. |
