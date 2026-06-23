# src/docsynthfab/reports/recommendations.py
# Recommended version ranges:
# - Python>=3.10,<3.14
#
# This module uses only the Python standard library.

from __future__ import annotations

from typing import Any, Dict, List


def build_recommendations(
    numeric: Dict[str, Any],
    categorical: Dict[str, Any],
    target_gap: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Build human-readable recommendations from diversity statistics."""
    recs: List[Dict[str, str]] = []

    has_table_dist = categorical.get("has_table", {}).get("distribution", {})
    table_ratio = float(has_table_dist.get("1", has_table_dist.get("True", 0.0)) or 0.0)

    if table_ratio < 0.10:
        recs.append(
            {
                "level": "warning",
                "area": "tables",
                "finding": f"Observed table page ratio is low: {table_ratio:.3f}.",
                "recommendation": "Increase content.has_table_prob and inspect table QC/layout failures.",
            }
        )

    has_eq_dist = categorical.get("has_equation", {}).get("distribution", {})
    eq_ratio = float(has_eq_dist.get("1", has_eq_dist.get("True", 0.0)) or 0.0)

    if eq_ratio < 0.10:
        recs.append(
            {
                "level": "info",
                "area": "latex",
                "finding": f"Observed equation page ratio is low: {eq_ratio:.3f}.",
                "recommendation": "Increase content.has_equation_prob or equation block placement diversity.",
            }
        )

    math_var = numeric.get("math_mask_ratio", {}).get("variance")

    if math_var is not None and float(math_var) < 1e-8:
        recs.append(
            {
                "level": "info",
                "area": "math_mask_variance",
                "finding": "math_mask_ratio variance is very low.",
                "recommendation": "Increase LaTeX expression size, equation count, or formula layout variation.",
            }
        )

    layout_entropy = categorical.get("layout_type", {}).get("entropy_bits")

    if layout_entropy is not None and float(layout_entropy) < 0.80:
        recs.append(
            {
                "level": "info",
                "area": "layout_diversity",
                "finding": f"layout_type entropy is low: {float(layout_entropy):.3f} bits.",
                "recommendation": "Balance layout.layout_type_dist or add more page families.",
            }
        )

    script_entropy = categorical.get("dominant_script", {}).get("entropy_bits")

    if script_entropy is not None and float(script_entropy) < 0.80:
        recs.append(
            {
                "level": "info",
                "area": "script_diversity",
                "finding": f"dominant_script entropy is low: {float(script_entropy):.3f} bits.",
                "recommendation": "Balance render.text.scripts_dist or add more multilingual content bank entries.",
            }
        )

    fallback_dist = categorical.get("fallback_used", {}).get("distribution", {})
    fallback_ratio = float(fallback_dist.get("1", fallback_dist.get("True", 0.0)) or 0.0)

    if fallback_ratio > 0.02:
        recs.append(
            {
                "level": "warning",
                "area": "fallback",
                "finding": f"Fallback ratio is {fallback_ratio:.3f}.",
                "recommendation": "QC or augmentation may be too aggressive. Inspect errors.jsonl and failed_pages.log.",
            }
        )

    for field, gap_obj in target_gap.items():
        signed = gap_obj.get("signed_gap", {})

        for k, gap in signed.items():
            if abs(float(gap)) >= 0.15:
                direction = "under-produced" if float(gap) < 0 else "over-produced"

                recs.append(
                    {
                        "level": "info",
                        "area": f"target_vs_observed:{field}",
                        "finding": f"`{k}` is {direction}; signed gap={float(gap):.3f}.",
                        "recommendation": f"Adjust the config distribution for `{field}` or inspect generation/QC constraints.",
                    }
                )

    if not recs:
        recs.append(
            {
                "level": "ok",
                "area": "overall",
                "finding": "No major diversity warnings were detected by the initial rules.",
                "recommendation": "Proceed to export and model benchmark.",
            }
        )

    return recs



