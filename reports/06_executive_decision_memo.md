# Executive Decision Memo — New Checkout Experience A/B Test

> **This is a synthetic-data learning project.** All numbers below come from
> a simulated dataset generated for educational purposes (seed=42), not from
> real customers. No launch decision should be made from this document
> alone in a real business context.

## 1. Executive Summary

We tested a new single-page checkout experience (treatment) against the
existing multi-step checkout (control), with the business question: **does
the new checkout increase purchase conversion without harming order value,
checkout reliability, or refund behavior?**

**Recommendation: Phased rollout with continued monitoring.**

The primary metric — conversion rate — is significantly higher for
treatment (12.16% vs. 9.95%, +2.21 percentage points, p<0.001), and none of
the three guardrails (checkout error rate, refund rate, AOV) show a
statistically significant regression after correcting for multiple testing.
On paper, all three of the Stage 1 pre-specified launch gates pass.

The most important caveat: this experiment was **underpowered** for its own
planned effect size (63.55% achieved power vs. an 80% target), and the
significant result reflects one specific random sample realizing a larger
effect (+2.21pp) than the design was originally sized to detect (+1pp). That
combination — technically passing gates, but on a less precise and
single-sample basis, with purchaser-only guardrails — argues against an
unconditional full launch and in favor of a controlled rollout with active
monitoring.

## 2. Experiment Design

- **Control**: existing multi-step checkout (cart → shipping → payment →
  confirm). **Treatment**: new single-page checkout.
- **Unit of randomization**: user. **Analysis unit**: each user's first
  checkout session in the window (same as randomization unit).
- **Sample size**: 9,938 control users, 10,062 treatment users (20,000
  total).
- **Duration**: 14 days (assumption, per Stage 1).
- **Primary metric**: purchase conversion rate (completed purchases /
  users who started checkout).
- **Guardrails**: average order value (AOV, purchasers only), checkout
  error rate (all sessions), refund rate (purchasers only, refunds within 7
  days).
- **Alpha**: 0.05 (two-sided) for the primary metric and guardrails; 0.01
  for the SRM check.
- **Planned design target**: 80% power to detect a +1 percentage point
  absolute lift off a 10% control baseline.

Full design detail: [docs/01_experiment_design.md](../docs/01_experiment_design.md).

## 3. Data-Quality Assessment

- Assignment counts: control 9,938 (49.69%), treatment 10,062 (50.31%).
- SRM check: chi-square = 0.7688, p = 0.3806 (threshold alpha = 0.01) —
  **no evidence of sample ratio mismatch**. This does not prove
  randomization was perfect; it means this test did not detect a deviation
  from the planned 50/50 split.
- No duplicate user IDs and no missing values were found in any required
  field (20,000 rows, 20,000 distinct user IDs).

Detail: [docs/03_sql_analysis.md](../docs/03_sql_analysis.md).

## 4. Primary Metric Result

| | n | conversions | rate |
|---|---|---|---|
| Control | 9,938 | 989 | 9.95% |
| Treatment | 10,062 | 1,224 | 12.16% |

- Absolute lift: **+2.21 percentage points**. Relative lift: **+22.24%**.
- 95% confidence interval on the absolute difference: **[1.34pp, 3.08pp]**.
- Two-sample proportion z-test: p < 0.001 (p ≈ 6.1×10⁻⁷). **Reject H0** at
  alpha = 0.05.

This dataset's underlying simulation was configured with a **+1
percentage point** treatment effect, but this specific random draw
realized a **+2.21 percentage point** difference — ordinary sampling
variation, not an error in the data or the test. Statistical significance
here confirms the observed difference is unlikely to be pure noise; it does
**not** mean a real launch would reproduce exactly +2.21pp — the true
effect could plausibly be anywhere in, or even outside, the 95% CI above,
and this being a single synthetic sample adds further uncertainty beyond
what the CI alone captures.

## 5. Guardrail Assessment

| Guardrail | Control | Treatment | Raw direction | Holm-adjusted p |
|---|---|---|---|---|
| Checkout error rate | 3.20% | 2.99% | lower (favorable) | 0.79 |
| Refund rate | 4.45% | 4.08% | lower (favorable) | 0.79 |
| AOV | $79.50 | $81.56 | higher (favorable) | 0.45 |

**No statistically significant guardrail deterioration was detected.** All
three guardrails also moved in a directionally favorable or neutral
direction for treatment, though none of these differences are individually
significant after Holm correction. This does **not** mean the guardrails
are identical between variants, and it does not mean there is definitely no
harm — it means this dataset, at this sample size, did not detect a
regression.

Refund rate and AOV are both calculated **among purchasers only**, per the
Stage 1 metric definitions. Purchasing is an outcome that happens *after*
treatment assignment and differs by variant (12.16% vs. 9.95% convert), so
the purchaser populations being compared are not themselves randomly
assigned groups — this conditions on a post-treatment variable and limits a
purely causal interpretation of these two guardrails specifically. In a
real experiment, **revenue per assigned user** (which folds conversion and
order value into one intent-to-treat-consistent metric) would be a useful
additional guardrail that avoids this conditioning issue.

## 6. Power and Experiment-Design Caveat

The experiment was designed to reach **80% power** to detect a **+1
percentage point** absolute lift off a 10% baseline, which required
approximately **14,751 users per group** (≈29,502 total). The actual
sample had approximately **10,000 users per group** (20,000 total) —
roughly two-thirds of the planned size. At that actual sample size, power
to detect the *planned* +1pp effect was only **63.55%**.

This does **not** mean the result is invalid — the observed effect (+2.21pp)
was large enough to reach significance despite the smaller sample. Nor does
it mean the original sample-size plan was validated; a true effect closer
to the planned +1pp could easily have been missed entirely at this sample
size, and the low achieved power limits how confidently this result should
generalize.

## 7. Recommendation and Rollout Plan

**Phased rollout with continued monitoring** is recommended because the
evidence is genuinely positive and passes every pre-specified gate, but the
underpowered design, single-sample nature of this result, and the
purchaser-only conditioning on two guardrails all argue for validating the
effect under real traffic before committing fully.

Suggested plan:
- Begin with a **limited share of traffic** routed to the new checkout
  (exact percentage to be set by product/eng based on infrastructure and
  risk tolerance — not specified in Stage 1).
- Monitor conversion rate, checkout error rate, refund rate, AOV, and
  **revenue per assigned user** throughout the rollout, not just at a single
  end-of-window snapshot.
- **Rollback thresholds must be pre-specified by product and risk
  stakeholders before rollout begins** — none were defined in Stage 1, and
  none are invented here.
- Allow refund observations to reach a mature window (Stage 1 defines
  refund rate over a 7-day post-purchase window) before finalizing any
  guardrail conclusion tied to a specific traffic cohort.
- Continue data collection, or run a properly powered confirmatory
  experiment (≈14,751 users/group, per Section 6), before declaring the
  effect fully validated.
- Set a review date at a pre-specified interval to decide on full launch,
  continued phasing, or rollback.

## 8. Limitations

- All data is **synthetic**, generated for this learning project — no real
  customers, transactions, or behavior are represented.
- The experiment was **underpowered** relative to its own planned MDE
  (63.55% vs. 80% target power).
- Results reflect **one realized random sample** (seed=42); a different
  draw could show a different lift, guardrail pattern, or significance
  outcome.
- Refund rate and AOV are **purchaser-only** metrics, conditioning on a
  post-treatment outcome, which limits pure causal interpretation.
- Segment findings (device, country, new/returning) in Stage 5 are
  **descriptive only** — no segment-level significance testing was
  performed, and no treatment-effect heterogeneity claim is made.
- This project provides no evidence about **long-term retention, novelty
  effects beyond the 14-day window, or fully mature refund behavior**
  beyond the simulated observation period.

## 9. Appendix

### Compact Results Table

| Metric | Control | Treatment | Diff / Lift | 95% CI | p-value | Holm-adj. p |
|---|---|---|---|---|---|---|
| Assignment (SRM) | 9,938 | 10,062 | χ²=0.7688 | — | 0.3806 | — |
| Conversion rate | 9.95% | 12.16% | +2.21pp (+22.24%) | [1.34pp, 3.08pp] | <0.001 | n/a (primary) |
| Checkout error rate | 3.20% | 2.99% | -0.21pp | [-0.69pp, 0.27pp] | 0.3949 | 0.7897 |
| Refund rate (purchasers) | 4.45% | 4.08% | -0.36pp | [-2.06pp, 1.33pp] | 0.6730 | 0.7897 |
| AOV (purchasers) | $79.50 | $81.56 | +$2.06 | [-$0.74, $4.87] | 0.1494 | 0.4482 |

### Stage Documentation
- [docs/01_experiment_design.md](../docs/01_experiment_design.md)
- [docs/02_data_generation.md](../docs/02_data_generation.md)
- [docs/03_sql_analysis.md](../docs/03_sql_analysis.md)
- [docs/04_statistical_testing.md](../docs/04_statistical_testing.md)
- [docs/05_visualization.md](../docs/05_visualization.md)

### Figures
- [outputs/figures/conversion_rate_ci.png](../outputs/figures/conversion_rate_ci.png)
- [outputs/figures/daily_conversion.png](../outputs/figures/daily_conversion.png)
- [outputs/figures/segment_conversion.png](../outputs/figures/segment_conversion.png)
- [outputs/figures/guardrail_metrics.png](../outputs/figures/guardrail_metrics.png)