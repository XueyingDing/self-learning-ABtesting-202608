# Stage 3 — SQL Metric Analysis

All metric calculations run in DuckDB via [sql/03_metric_analysis.sql](../sql/03_metric_analysis.sql),
executed by [src/run_sql_analysis.py](../src/run_sql_analysis.py) (Python only
runs the SQL and saves outputs — no metric math in Python). Source data is
unchanged from Stage 2: [data/ab_test_data.csv](../data/ab_test_data.csv).

## Dataset Grain
One row per eligible user = unit of randomization = analysis unit
(per Stage 1). No joins or fan-out occur anywhere in this SQL — every query
either aggregates this grain or reads it directly.

## Metric Denominators (from Stage 1, enforced in SQL)
| Metric | Formula | Denominator |
|---|---|---|
| Conversion rate | `SUM(converted) / COUNT(*)` | all eligible users (all rows) |
| AOV | `SUM(order_revenue) / SUM(converted)` | purchasers only |
| Checkout error rate | `SUM(had_checkout_error) / COUNT(*)` | all sessions started |
| Refund rate | `SUM(refunded) / SUM(converted)` | purchasers only |

Every ratio is wrapped in `NULLIF(denominator, 0)` to avoid divide-by-zero.
Rounding is applied only in each query's final `SELECT`; all intermediate
CTEs keep unrounded values.

## SQL Techniques Used
- CTEs to keep each metric's aggregation isolated and readable before a
  final join (`overall_metrics` block).
- `UNION ALL` with a `segment_type` label to combine three segment cuts
  (device_type, country, new_vs_returning_user) into one tidy table.
- Window function `SUM(...) OVER (PARTITION BY variant ORDER BY
  assignment_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` to
  derive cumulative eligible/converted users per variant from the daily
  grain, without a self-join.
- Explicit column lists everywhere (no `SELECT *`) including the base view.

## Data Quality Checks (actual results)
- Total rows: **20,000**
- Distinct user IDs: **20,000**
- Duplicate user IDs: **0**
- Missing values: **0** in every required field (user_id, variant,
  assignment_date, converted, order_revenue, had_checkout_error, refunded)

## Overall Metrics by Variant (actual results)
| variant | assigned_users | assignment_pct | conversion_rate | AOV | error_rate | refund_rate |
|---|---|---|---|---|---|---|
| control | 9,938 | 49.69% | 9.95% | $79.50 | 3.20% | 4.45% |
| treatment | 10,062 | 50.31% | 12.16% | $81.56 | 2.99% | 4.08% |

These match the Stage 2 pandas validation output exactly, as expected since
both compute the same formulas over the same unmodified CSV.

## Notable Segment-Level Descriptive Differences (not yet tested)
- **Device type**: mobile has the lowest conversion in both arms (control
  8.92%, treatment 11.62%) vs. desktop (control 11.29%, treatment 12.93%) —
  consistent with the simulated device effect from Stage 2.
- **New vs. returning**: returning users convert higher in both arms
  (control 11.39%, treatment 13.33%) than new users (control 9.02%,
  treatment 11.36%) — consistent with the simulated returning-user effect.
- **Country**: treatment leads control in every country (range: control
  8.90%–11.31%, treatment 11.82%–12.49%); CA shows the largest gap
  (+2.92pp) in this single dataset draw.
- All of the above are **descriptive differences only** — sample sizes per
  cell range from ~700 to ~5,000, no confidence intervals or significance
  tests have been computed, and none of these gaps should be treated as
  reliable findings yet.

## Daily / Cumulative Trend (actual results)
- 14 days per variant, as designed.
- Cumulative conversion rate converges toward the overall rate by day 14
  (control 9.95%, treatment 12.16%), with daily rates bouncing around that
  level — no obvious trend or novelty-effect decay visible by eye in this
  draw, but this has not been formally tested.

## Explicitly Not Done in This Stage
- No hypothesis tests, p-values, or confidence intervals.
- No sample ratio mismatch significance test (the 49.69/50.31 split above is
  descriptive only).
- No business recommendation.