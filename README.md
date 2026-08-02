# Checkout A/B Test — End-to-End Analysis

## Business Scenario
A product team is testing whether a new checkout experience improves purchase
conversion compared to the current (control) checkout flow. Users are randomly
assigned to control or treatment, and we analyze the resulting synthetic data
to recommend whether to ship the new experience.

## Hypothesis
The new checkout experience (treatment) increases purchase conversion rate
relative to the existing checkout (control).

- H0: conversion_rate(treatment) = conversion_rate(control)
- H1: conversion_rate(treatment) != conversion_rate(control)

## Primary Metric
- **Purchase conversion rate**: (# users who complete a purchase) / (# users who start checkout)

## Guardrail Metrics
- **Average order value (AOV)** — treatment shouldn't reduce revenue per order
- **Checkout error rate** — treatment shouldn't degrade experience
- **Refund/cancellation rate** — treatment shouldn't induce buyer's remorse

Full formulas and exact denominators: [docs/01_experiment_design.md](docs/01_experiment_design.md).

## Project Checklist (7 Stages)
- [x] 1. Experiment design ([docs/01_experiment_design.md](docs/01_experiment_design.md))
- [x] 2. Synthetic data generation ([docs/02_data_generation.md](docs/02_data_generation.md))
- [x] 3. SQL metric analysis ([docs/03_sql_analysis.md](docs/03_sql_analysis.md))
- [x] 4. Python statistical testing ([docs/04_statistical_testing.md](docs/04_statistical_testing.md))
- [x] 5. Visualization ([docs/05_visualization.md](docs/05_visualization.md))
- [x] 6. Business recommendation write-up ([reports/06_executive_decision_memo.md](reports/06_executive_decision_memo.md))
- [x] 7. Final review & polish

## Project Structure
```
.
├── CLAUDE.md
├── README.md
├── requirements.txt
├── data/                 # synthetic dataset (data/ab_test_data.csv)
├── docs/                 # Stage 1-5 methodology write-ups
├── sql/                  # DuckDB metric queries
├── src/                  # Python scripts (data gen, SQL runner, stats, viz)
├── outputs/
│   ├── sql/              # metric CSVs from DuckDB
│   ├── statistics/       # test_results.csv, power_analysis.csv
│   └── figures/          # the four PNG charts
└── reports/              # executive decision memo
```

## Project Summary
An end-to-end, synthetic-data A/B testing project: data generation → SQL
metric analysis (DuckDB) → Python statistical testing (scipy) →
visualization (matplotlib) → an executive decision memo. All numbers in
this README and in the memo come from the outputs actually produced in
`outputs/` — nothing here is fabricated or hand-typed independent of those
files.

## Final Business Conclusions
Full detail and reasoning: [reports/06_executive_decision_memo.md](reports/06_executive_decision_memo.md).

- **Result**: Treatment conversion rate (12.16%) was significantly higher
  than control (9.95%), +2.21pp absolute / +22.24% relative, 95% CI
  [1.34pp, 3.08pp], p<0.001. No statistically significant guardrail
  deterioration was detected (checkout error rate, refund rate, AOV) after
  Holm correction.
- **Recommendation: Phased rollout with continued monitoring** — not a full
  launch, and not "do not launch." All three Stage 1 launch gates
  technically pass: the primary metric improved significantly, no guardrail
  showed statistically significant deterioration after Holm correction, and
  there was no evidence of sample ratio mismatch. But power at the actual
  sample size for the planned +1pp effect was only 63.55% against an 80%
  target, so the result should be validated under real traffic with active
  guardrail monitoring before a full commitment.
- **Caveats / next steps**: synthetic data, one realized random sample,
  underpowered design, purchaser-only guardrail metrics (refund rate, AOV)
  that condition on a post-treatment outcome, descriptive-only segment
  results, and no evidence on long-term retention or fully mature refund
  behavior. Next step: stakeholders pre-specify rollback thresholds, then
  begin a limited-traffic rollout or a properly powered confirmatory
  experiment (~14,751 users/group).

### Figures
- [outputs/figures/conversion_rate_ci.png](outputs/figures/conversion_rate_ci.png)
- [outputs/figures/daily_conversion.png](outputs/figures/daily_conversion.png)
- [outputs/figures/segment_conversion.png](outputs/figures/segment_conversion.png)
- [outputs/figures/guardrail_metrics.png](outputs/figures/guardrail_metrics.png)

## Reproducing This Project
```bash
pip install -r requirements.txt

python src/generate_data.py          # Stage 2: synthetic data -> data/ab_test_data.csv
python src/run_sql_analysis.py       # Stage 3: DuckDB metrics -> outputs/sql/*.csv
python src/run_statistical_tests.py  # Stage 4: hypothesis tests -> outputs/statistics/*.csv
python src/create_visualizations.py  # Stage 5: figures -> outputs/figures/*.png
```

## Skills Demonstrated
- Experiment design and metric definition (primary metric, guardrails,
  randomization/analysis units, launch decision rule)
- Synthetic data generation with a controlled, documented treatment effect
- SQL analysis in DuckDB, including CTEs, `UNION ALL` segment rollups, and
  window functions for cumulative metrics
- Two-sample proportion tests, Welch's t-test, Holm-Bonferroni correction,
  and a chi-square sample-ratio-mismatch test
- Power and sample-size analysis, including diagnosing an underpowered
  design after the fact
- Analytical, business-readable visualization (matplotlib, no dual axes,
  colorblind-safe fixed palette)
- Executive decision communication translating statistical results into a
  bounded business recommendation
- A reproducible, AI-assisted analytics workflow with a documented,
  stage-by-stage audit trail

### Disclosure
- The dataset is entirely **synthetic**, generated for this learning
  project — no real customer or transaction data was used.
- **AI (Claude Code) assisted with building this repository** — writing the
  generation script, SQL, statistical tests, visualizations, and this
  documentation, one stage at a time.
- Analytical assumptions, code execution, and outputs were **reviewed at
  each stage rather than accepted without validation** — scripts were run
  and their actual console/file output (not assumed output) is what's
  reported throughout the docs and this README.
- This is a **learning and portfolio project, not production software**.