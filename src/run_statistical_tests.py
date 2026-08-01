"""
Stage 4: statistical testing for the checkout A/B test.

Reads data/ab_test_data.csv (unmodified since Stage 2) and runs:
  A. Sample ratio mismatch (chi-square goodness-of-fit)
  B. Primary metric: two-sample proportion test (conversion rate)
  C. Guardrail metrics: proportion tests (error rate, refund rate) +
     Welch's t-test (AOV), with Holm correction across the three guardrails
  D. Power / sample-size analysis using the PLANNED effect (control=10%,
     MDE=+1pp), not the observed lift

Formulas are written out explicitly (not hidden in helper libraries) so the
math stays visible and educational. Only scipy.stats.norm/t/chisquare are
used for standard-normal/t/chi-square distribution lookups.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT_DIR / "data" / "ab_test_data.csv"
OUTPUT_DIR = ROOT_DIR / "outputs" / "statistics"

ALPHA = 0.05  # pre-specified in docs/01_experiment_design.md section 11
SRM_ALPHA = 0.01  # pre-specified SRM threshold, docs/01_experiment_design.md section 10/11


def holm_correction(p_values: list) -> list:
    """Holm-Bonferroni step-down adjustment. Returns adjusted p-values in
    the ORIGINAL input order (not sorted)."""
    m = len(p_values)
    order = np.argsort(p_values)  # ascending
    sorted_p = np.array(p_values)[order]

    adjusted_sorted = np.empty(m)
    running_max = 0.0
    for i in range(m):
        candidate = (m - i) * sorted_p[i]
        running_max = max(running_max, candidate)
        adjusted_sorted[i] = min(running_max, 1.0)

    # scatter back to original order
    adjusted = np.empty(m)
    adjusted[order] = adjusted_sorted
    return adjusted.tolist()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_PATH)

    control = df[df["variant"] == "control"]
    treatment = df[df["variant"] == "treatment"]

    test_rows = []

    # ---------------------------------------------------------------
    # A. Sample ratio mismatch: chi-square goodness-of-fit vs. 50/50
    # ---------------------------------------------------------------
    n_total = len(df)
    observed = [len(control), len(treatment)]
    expected = [n_total / 2, n_total / 2]  # planned 50/50 allocation
    chi2_stat, srm_p = stats.chisquare(f_obs=observed, f_exp=expected)

    test_rows.append({
        "test_id": "A_srm",
        "test_name": "Sample ratio mismatch (chi-square goodness-of-fit)",
        "metric": "assignment_count",
        "alpha_used": SRM_ALPHA,
        "group_a_label": "control",
        "group_a_n": observed[0],
        "group_a_value": observed[0],
        "group_b_label": "treatment",
        "group_b_n": observed[1],
        "group_b_value": observed[1],
        "absolute_diff": np.nan,
        "relative_diff_pct": np.nan,
        "ci_lower": np.nan,
        "ci_upper": np.nan,
        "statistic_type": "chi2",
        "statistic_value": chi2_stat,
        "p_value_raw": srm_p,
        "p_value_holm_adjusted": np.nan,  # SRM is not part of guardrail correction
        "reject_null": bool(srm_p < SRM_ALPHA),
        "notes": (
            f"Expected {expected[0]:.0f}/{expected[1]:.0f} under 50/50 allocation. "
            "A non-significant result does NOT prove perfect randomization -- it "
            "only means there is insufficient evidence of SRM at this alpha."
        ),
    })

    # ---------------------------------------------------------------
    # B. Primary metric: conversion rate, two-sample proportion test
    # ---------------------------------------------------------------
    n1, n2 = len(control), len(treatment)  # control, treatment
    x1, x2 = control["converted"].sum(), treatment["converted"].sum()
    p1, p2 = x1 / n1, x2 / n2

    abs_lift = p2 - p1
    rel_lift_pct = (abs_lift / p1) * 100

    # Pooled SE for the null-hypothesis test (assumes p1 == p2 under H0)
    p_pool = (x1 + x2) / (n1 + n2)
    se_pooled = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z_stat = abs_lift / se_pooled
    p_value_primary = 2 * (1 - stats.norm.cdf(abs(z_stat)))  # two-sided, per Stage 1

    # Unpooled SE for the confidence interval (does not assume p1 == p2)
    se_unpooled = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    z_crit = stats.norm.ppf(1 - ALPHA / 2)
    ci_lower = abs_lift - z_crit * se_unpooled
    ci_upper = abs_lift + z_crit * se_unpooled

    test_rows.append({
        "test_id": "B_primary",
        "test_name": "Primary metric: conversion rate (two-sample proportion z-test)",
        "metric": "conversion_rate",
        "alpha_used": ALPHA,
        "group_a_label": "control",
        "group_a_n": n1,
        "group_a_value": p1,
        "group_b_label": "treatment",
        "group_b_n": n2,
        "group_b_value": p2,
        "absolute_diff": abs_lift,
        "relative_diff_pct": rel_lift_pct,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "statistic_type": "z",
        "statistic_value": z_stat,
        "p_value_raw": p_value_primary,
        "p_value_holm_adjusted": np.nan,  # primary metric is not guardrail-corrected
        "reject_null": bool(p_value_primary < ALPHA),
        "notes": "SE_pooled used for z-stat/p-value; SE_unpooled used for the 95% CI, per spec.",
    })

    # ---------------------------------------------------------------
    # C. Guardrail metrics
    # ---------------------------------------------------------------

    # C1. Checkout error rate -- denominator = all sessions started (all rows)
    n1e, n2e = len(control), len(treatment)
    x1e, x2e = control["had_checkout_error"].sum(), treatment["had_checkout_error"].sum()
    p1e, p2e = x1e / n1e, x2e / n2e
    diff_e = p2e - p1e
    p_pool_e = (x1e + x2e) / (n1e + n2e)
    se_pooled_e = np.sqrt(p_pool_e * (1 - p_pool_e) * (1 / n1e + 1 / n2e))
    z_e = diff_e / se_pooled_e
    p_e = 2 * (1 - stats.norm.cdf(abs(z_e)))
    se_unpooled_e = np.sqrt(p1e * (1 - p1e) / n1e + p2e * (1 - p2e) / n2e)
    ci_e = (diff_e - z_crit * se_unpooled_e, diff_e + z_crit * se_unpooled_e)

    # C2. Refund rate -- denominator = completed purchases only (Stage 1 def.)
    control_purchasers = control[control["converted"] == 1]
    treatment_purchasers = treatment[treatment["converted"] == 1]
    n1r, n2r = len(control_purchasers), len(treatment_purchasers)
    x1r, x2r = control_purchasers["refunded"].sum(), treatment_purchasers["refunded"].sum()
    p1r, p2r = x1r / n1r, x2r / n2r
    diff_r = p2r - p1r
    p_pool_r = (x1r + x2r) / (n1r + n2r)
    se_pooled_r = np.sqrt(p_pool_r * (1 - p_pool_r) * (1 / n1r + 1 / n2r))
    z_r = diff_r / se_pooled_r
    p_r = 2 * (1 - stats.norm.cdf(abs(z_r)))
    se_unpooled_r = np.sqrt(p1r * (1 - p1r) / n1r + p2r * (1 - p2r) / n2r)
    ci_r = (diff_r - z_crit * se_unpooled_r, diff_r + z_crit * se_unpooled_r)

    # C3. AOV -- purchasers only (Stage 1 def.), Welch's t-test (unequal variance)
    control_aov = control_purchasers["order_revenue"]
    treatment_aov = treatment_purchasers["order_revenue"]
    t_stat, p_aov = stats.ttest_ind(treatment_aov, control_aov, equal_var=False)
    mean_diff_aov = treatment_aov.mean() - control_aov.mean()

    # Welch-Satterthwaite CI for the mean difference (matches scipy's df internally)
    s1sq_n1 = control_aov.var(ddof=1) / n1r
    s2sq_n2 = treatment_aov.var(ddof=1) / n2r
    se_aov = np.sqrt(s1sq_n1 + s2sq_n2)
    df_welch = (s1sq_n1 + s2sq_n2) ** 2 / (
        s1sq_n1 ** 2 / (n1r - 1) + s2sq_n2 ** 2 / (n2r - 1)
    )
    t_crit = stats.t.ppf(1 - ALPHA / 2, df_welch)
    ci_aov = (mean_diff_aov - t_crit * se_aov, mean_diff_aov + t_crit * se_aov)

    # Holm correction across the three guardrail tests only
    guardrail_p_raw = [p_e, p_r, p_aov]
    guardrail_p_holm = holm_correction(guardrail_p_raw)

    test_rows.append({
        "test_id": "C1_error_rate",
        "test_name": "Guardrail: checkout error rate (two-sample proportion z-test)",
        "metric": "checkout_error_rate",
        "alpha_used": ALPHA,
        "group_a_label": "control",
        "group_a_n": n1e,
        "group_a_value": p1e,
        "group_b_label": "treatment",
        "group_b_n": n2e,
        "group_b_value": p2e,
        "absolute_diff": diff_e,
        "relative_diff_pct": (diff_e / p1e) * 100,
        "ci_lower": ci_e[0],
        "ci_upper": ci_e[1],
        "statistic_type": "z",
        "statistic_value": z_e,
        "p_value_raw": guardrail_p_raw[0],
        "p_value_holm_adjusted": guardrail_p_holm[0],
        "reject_null": bool(guardrail_p_holm[0] < ALPHA),
        "notes": "Denominator = all sessions started, per Stage 1.",
    })

    test_rows.append({
        "test_id": "C2_refund_rate",
        "test_name": "Guardrail: refund rate (two-sample proportion z-test)",
        "metric": "refund_rate",
        "alpha_used": ALPHA,
        "group_a_label": "control",
        "group_a_n": n1r,
        "group_a_value": p1r,
        "group_b_label": "treatment",
        "group_b_n": n2r,
        "group_b_value": p2r,
        "absolute_diff": diff_r,
        "relative_diff_pct": (diff_r / p1r) * 100,
        "ci_lower": ci_r[0],
        "ci_upper": ci_r[1],
        "statistic_type": "z",
        "statistic_value": z_r,
        "p_value_raw": guardrail_p_raw[1],
        "p_value_holm_adjusted": guardrail_p_holm[1],
        "reject_null": bool(guardrail_p_holm[1] < ALPHA),
        "notes": "Denominator = completed purchases only, per Stage 1.",
    })

    test_rows.append({
        "test_id": "C3_aov",
        "test_name": "Guardrail: AOV (Welch's independent-samples t-test)",
        "metric": "aov",
        "alpha_used": ALPHA,
        "group_a_label": "control",
        "group_a_n": n1r,
        "group_a_value": control_aov.mean(),
        "group_b_label": "treatment",
        "group_b_n": n2r,
        "group_b_value": treatment_aov.mean(),
        "absolute_diff": mean_diff_aov,
        "relative_diff_pct": (mean_diff_aov / control_aov.mean()) * 100,
        "ci_lower": ci_aov[0],
        "ci_upper": ci_aov[1],
        "statistic_type": "t",
        "statistic_value": t_stat,
        "p_value_raw": guardrail_p_raw[2],
        "p_value_holm_adjusted": guardrail_p_holm[2],
        "reject_null": bool(guardrail_p_holm[2] < ALPHA),
        "notes": (
            "Purchasers only, per Stage 1. Welch's t-test assumes approx. normal "
            "sampling distribution of the mean (reasonable here given n>1000 per "
            "group and the CLT) but does not require equal variances; it is still "
            "sensitive to strong skew/outliers in the underlying transaction values."
        ),
    })

    test_results_df = pd.DataFrame(test_rows)
    test_results_path = OUTPUT_DIR / "test_results.csv"
    test_results_df.to_csv(test_results_path, index=False)

    # ---------------------------------------------------------------
    # D. Power / sample-size analysis using PLANNED assumptions
    # ---------------------------------------------------------------
    p_planned_control = 0.10
    mde_abs = 0.01
    p_planned_treatment = p_planned_control + mde_abs
    power_target = 0.80

    p_bar_planned = (p_planned_control + p_planned_treatment) / 2
    z_alpha2 = stats.norm.ppf(1 - ALPHA / 2)
    z_power = stats.norm.ppf(power_target)

    # Standard two-proportion sample-size formula (normal approximation),
    # equal allocation per group.
    numerator = (
        z_alpha2 * np.sqrt(2 * p_bar_planned * (1 - p_bar_planned))
        + z_power * np.sqrt(
            p_planned_control * (1 - p_planned_control)
            + p_planned_treatment * (1 - p_planned_treatment)
        )
    ) ** 2
    denominator = mde_abs ** 2
    required_n_per_group = numerator / denominator
    required_n_total = 2 * required_n_per_group

    # Achieved power using the ACTUAL sample sizes in this dataset, but the
    # PLANNED effect size (not the observed +2.21pp lift).
    n1_actual, n2_actual = len(control), len(treatment)
    p_bar_actual = (n1_actual * p_planned_control + n2_actual * p_planned_treatment) / (
        n1_actual + n2_actual
    )
    se_null_actual = np.sqrt(
        p_bar_actual * (1 - p_bar_actual) * (1 / n1_actual + 1 / n2_actual)
    )
    se_alt_actual = np.sqrt(
        p_planned_control * (1 - p_planned_control) / n1_actual
        + p_planned_treatment * (1 - p_planned_treatment) / n2_actual
    )
    margin = z_alpha2 * se_null_actual
    achieved_power = stats.norm.cdf(
        (mde_abs - margin) / se_alt_actual
    ) + stats.norm.cdf((-mde_abs - margin) / se_alt_actual)

    power_df = pd.DataFrame([{
        "planned_control_rate": p_planned_control,
        "planned_treatment_rate": p_planned_treatment,
        "minimum_detectable_absolute_lift": mde_abs,
        "alpha": ALPHA,
        "target_power": power_target,
        "required_n_per_group": required_n_per_group,
        "required_n_total": required_n_total,
        "actual_n_control": n1_actual,
        "actual_n_treatment": n2_actual,
        "actual_n_total": n1_actual + n2_actual,
        "achieved_power_at_actual_n": achieved_power,
    }])
    power_path = OUTPUT_DIR / "power_analysis.csv"
    power_df.to_csv(power_path, index=False)

    # ---------------------------------------------------------------
    # Console report
    # ---------------------------------------------------------------
    print("=== A. Sample ratio mismatch ===")
    print(f"observed control/treatment: {observed[0]}/{observed[1]}")
    print(f"expected control/treatment: {expected[0]:.1f}/{expected[1]:.1f}")
    print(f"chi2 = {chi2_stat:.4f}, p = {srm_p:.4f} (alpha={SRM_ALPHA})")

    print("\n=== B. Primary metric: conversion rate ===")
    print(f"control: n={n1}, x={x1}, rate={p1:.4%}")
    print(f"treatment: n={n2}, x={x2}, rate={p2:.4%}")
    print(f"absolute lift={abs_lift:.4%}, relative lift={rel_lift_pct:.2f}%")
    print(f"se_pooled={se_pooled:.5f}, se_unpooled={se_unpooled:.5f}")
    print(f"95% CI (unpooled): [{ci_lower:.4%}, {ci_upper:.4%}]")
    print(f"z={z_stat:.4f}, p={p_value_primary:.6f}, alpha={ALPHA}")
    print(f"reject H0: {p_value_primary < ALPHA}")

    print("\n=== C. Guardrails (raw p -> Holm-adjusted p) ===")
    print(f"error_rate: raw p={p_e:.4f} -> holm p={guardrail_p_holm[0]:.4f}")
    print(f"refund_rate: raw p={p_r:.4f} -> holm p={guardrail_p_holm[1]:.4f}")
    print(f"aov: raw p={p_aov:.4f} -> holm p={guardrail_p_holm[2]:.4f}")

    print("\n=== D. Power / sample-size analysis (planned assumptions) ===")
    print(f"required n per group: {required_n_per_group:.0f}")
    print(f"required n total: {required_n_total:.0f}")
    print(f"achieved power at actual n ({n1_actual}+{n2_actual}): {achieved_power:.4f}")

    print(f"\nSaved: {test_results_path}")
    print(f"Saved: {power_path}")


if __name__ == "__main__":
    main()