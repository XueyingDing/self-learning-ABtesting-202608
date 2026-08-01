# Stage 4 — Statistical Testing

Run by [src/run_statistical_tests.py](../src/run_statistical_tests.py) against
the unmodified [data/ab_test_data.csv](../data/ab_test_data.csv). Outputs:
[outputs/statistics/test_results.csv](../outputs/statistics/test_results.csv),
[outputs/statistics/power_analysis.csv](../outputs/statistics/power_analysis.csv).

Alpha = 0.05 and a two-sided primary test, per
[docs/01_experiment_design.md](01_experiment_design.md) section 11 (both were
already specified there, not a new assumption). SRM threshold = 0.01, also
from Stage 1.

## Methods
- **SRM**: chi-square goodness-of-fit, observed counts vs. 50/50 expected.
- **Primary metric (conversion rate)**: two-sample proportion z-test —
  pooled SE for the z-statistic/p-value (assumes H0: p1=p2), unpooled SE for
  the 95% CI (does not assume equal proportions).
- **Guardrails**: error rate and refund rate use the same proportion-test
  approach, each with its Stage-1 denominator (error rate: all sessions;
  refund rate: purchasers only). AOV (purchasers only) uses Welch's
  independent-samples t-test (unequal-variance) with a Welch-Satterthwaite
  CI for the mean difference. Holm correction applied across these three
  guardrail p-values only — not to the primary metric or SRM.
- **Power/sample size**: standard two-proportion normal-approximation
  formula, using the **planned** assumptions (control=10%, MDE=+1pp,
  alpha=0.05, power=80%), not the observed +2.21pp lift.

## Actual Results

**A. SRM**: observed 9,938/10,062 vs. expected 10,000/10,000. χ²=0.7688,
p=0.3806 (alpha=0.01) → not significant. This does **not** prove perfect
randomization — it means there is insufficient evidence of SRM at this
threshold.

**B. Primary metric (conversion rate)**:
| | n | conversions | rate |
|---|---|---|---|
| control | 9,938 | 989 | 9.95% |
| treatment | 10,062 | 1,224 | 12.16% |

Absolute lift +2.21pp, relative lift +22.24%. SE_pooled=0.00444,
SE_unpooled=0.00443. 95% CI (unpooled): **[1.34pp, 3.08pp]**. z=4.99,
**p<0.000001**. At alpha=0.05: **reject H0**.

**C. Guardrails** (raw p → Holm-adjusted p):
| guardrail | control | treatment | raw p | holm p | reject H0 |
|---|---|---|---|---|---|
| error rate | 3.20% | 2.99% | 0.3949 | 0.7897 | No |
| refund rate | 4.45% | 4.08% | 0.6730 | 0.7897 | No |
| AOV | $79.50 | $81.56 | 0.1494 | 0.4482 | No |

No guardrail shows a statistically significant difference after correction.
AOV limitation: Welch's t-test assumes an approximately normal sampling
distribution of the *mean* (reasonable here with >900 purchasers per group,
via the CLT) but the underlying transaction values are right-skewed
(lognormal), so it does not describe the distribution of individual
transactions and can be sensitive to skew/outliers with smaller samples.

**D. Power / sample size** (planned assumptions, not observed lift):
- Required n per group: **14,751**; required total: **29,502**
- Actual n: 9,938 + 10,062 = 20,000
- **Achieved power at actual n (to detect the planned +1pp effect): 63.55%**
  — below the 80% target. This dataset is undersized relative to what the
  original design called for.

## Interpretation

Three distinct decisions, not to be conflated:
- **Data-quality decision**: no SRM detected, no duplicates/missing values
  (Stage 3) → the dataset is clean enough to analyze.
- **Statistical decision**: primary metric is significant at alpha=0.05
  (p<0.000001), no guardrail regression detected after Holm correction.
- **Practical/business decision**: not made in this stage — reserved for
  Stage 6.

**On the effect size**: the data-generating process (Stage 2) was configured
with a **+1pp** treatment effect, but this particular random sample
(seed=42) realized a **+2.21pp** difference. This is expected sampling
variation, not an error — a single draw from a random process will not
exactly reproduce its generating parameter, especially combined with the
device/returning-user effects also present in the simulation. The random
seed was not changed and data was not regenerated to chase the +1pp figure.

Also worth flagging: despite reaching significance here, the achieved power
(63.55%) for the *planned* effect is below the 80% target — this sample size
would not reliably detect a true +1pp lift across repeated experiments. The
significance observed in this run reflects the larger realized effect in
this specific draw, not evidence that the experiment was adequately powered
for its original design target.

## Explicitly Not Done in This Stage
- No significance tests for individual countries, devices, or segments.
- No charts.
- No final launch recommendation.