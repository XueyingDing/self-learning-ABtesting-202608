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

## Preliminary Primary Metric
- **Purchase conversion rate**: (# users who complete a purchase) / (# users who start checkout)

## Preliminary Guardrail Metrics
- **Average order value (AOV)** — treatment shouldn't reduce revenue per order
- **Checkout latency / error rate** — treatment shouldn't degrade experience
- **Refund/cancellation rate** — treatment shouldn't induce buyer's remorse

*(Metrics may be refined once data generation begins.)*

## Project Checklist (7 Stages)
- [x] 1. Experiment design ([docs/01_experiment_design.md](docs/01_experiment_design.md))
- [x] 2. Synthetic data generation ([docs/02_data_generation.md](docs/02_data_generation.md))
- [x] 3. SQL metric analysis ([docs/03_sql_analysis.md](docs/03_sql_analysis.md))
- [ ] 4. Python statistical testing (scipy)
- [ ] 5. Visualization (matplotlib)
- [ ] 6. Business recommendation write-up
- [ ] 7. Final review & polish

## Planned Folder Structure
```
.
├── CLAUDE.md
├── README.md
├── data/           # synthetic datasets (generated, not hand-written)
├── sql/            # metric queries
├── notebooks_or_scripts/  # Python analysis (stats + viz)
└── outputs/        # charts, summary tables
```

## Final Business Conclusions
*(Placeholder — to be filled in after Stage 5.)*

- Result:
- Recommendation:
- Caveats / next steps: