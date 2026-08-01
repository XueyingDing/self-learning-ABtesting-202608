# Experiment Design — New Checkout Experience

## 1. Business Context and Product Change
The current checkout flow is a multi-step process (cart → shipping → payment →
confirm). The new checkout experience is a streamlined single-page checkout
that reduces steps and form fields, aiming to reduce drop-off and increase
purchase conversion.

## 2. Target Users and Eligibility Criteria
- Users who reach the checkout start page (i.e., have at least one item in
  cart and click "Checkout").
- **Assumption:** Web platform only (desktop + mobile web), logged-in and
  guest users both eligible.
- **Assumption:** New users and returning users both eligible (no tenure
  restriction), to keep the synthetic dataset simple.
- Excluded: internal/test accounts (**assumption**: flagged via an
  `is_internal` field in synthetic data).

## 3. Control and Treatment Experiences
- **Control (A):** existing multi-step checkout (cart → shipping → payment →
  confirm).
- **Treatment (B):** new single-page checkout (all fields on one page).
- **Assumption:** Both variants use the same payment backend and pricing;
  only the UI flow differs.

## 4. Null and Alternative Hypotheses
- H0: conversion_rate(B) = conversion_rate(A)
- H1: conversion_rate(B) != conversion_rate(A)
- **Assumption:** two-sided test, since a regression is possible and should
  be caught, not just an improvement.

## 5. Primary Metric
**Purchase conversion rate**

```
conversion_rate = (# users with >=1 completed purchase during checkout session)
                   / (# users who started checkout)
```

Computed per variant, over the experiment window.

## 6. Guardrail Metrics
1. **Average order value (AOV)**
   `AOV = total purchase revenue / # completed purchases`
   (protects against conversion gains from lower-value orders)

2. **Checkout error rate**
   `error_rate = # checkout sessions with >=1 payment/form error
                 / # checkout sessions started`
   (protects against the new flow being buggier)

3. **Refund rate**
   `refund_rate = # purchases refunded within 7 days
                  / # completed purchases`
   (protects against buyer's remorse / accidental submits from the
   condensed flow)

## 7. Unit of Randomization
- **User** (via a persistent `user_id` or, for guests, a stable device/session
  cookie ID). **Assumption:** synthetic data assigns variant at the user
  level and keeps it fixed for the user's entire participation in the
  experiment (no re-randomization).

## 8. Analysis Unit
- **User-level checkout session**: each user's first checkout attempt during
  the experiment window is the unit analyzed for conversion. **Assumption:**
  repeat checkout attempts by the same user are collapsed to their first
  attempt, to avoid double-counting and unit-of-analysis mismatch with the
  unit of randomization.

## 9. Experiment Duration Assumptions
- **Assumption:** 14-day run, covering two full weekly cycles to average out
  day-of-week effects.
- **Assumption:** Minimum detectable effect (MDE) of ~2 percentage points on
  a baseline conversion rate of ~10%, at 80% power and alpha = 0.05 — used
  only to justify sample size when synthetic data is generated later, not
  computed in this document.

## 10. Main Risks
- **Novelty effects:** early treatment lift may reflect curiosity, not a
  durable improvement — mitigate by comparing week-1 vs week-2 effect size.
- **Sample ratio mismatch (SRM):** if actual traffic split deviates from the
  intended 50/50, results may be biased by a broken randomization or logging
  gap — check with a chi-square goodness-of-fit test on assignment counts.
- **Instrumentation problems:** missing or duplicated conversion events would
  distort the primary metric — mitigate by validating event counts against
  session counts before analysis.
- **Multiple testing:** testing one primary metric plus three guardrails
  inflates false-positive risk — mitigate by treating guardrails as
  directional checks (not stopping criteria) and only formally testing the
  primary metric, or applying a Bonferroni-style correction if guardrails are
  also formally tested.

## 11. Launch Decision Rule
Ship the new checkout (treatment) if **all** of the following hold:
1. Primary metric: conversion_rate(B) is statistically significantly higher
   than conversion_rate(A) (two-sided test, alpha = 0.05).
2. No guardrail metric regresses beyond its tolerance:
   - AOV does not drop by more than 5% (**assumption**).
   - Error rate does not increase (any statistically significant increase
     blocks launch).
   - Refund rate does not increase by more than 1 percentage point
     (**assumption**).
3. No SRM detected (chi-square p > 0.01 on assignment split).

If the primary metric is flat/negative, do not ship. If the primary metric is
positive but a guardrail regresses beyond tolerance, escalate for manual
review rather than auto-deciding.