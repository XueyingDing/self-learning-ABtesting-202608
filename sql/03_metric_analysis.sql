-- Stage 3: SQL metric analysis for the checkout A/B test.
-- Grain of ab_test_data.csv: one row per eligible user (= unit of
-- randomization = analysis unit, per docs/01_experiment_design.md).
-- Denominators below follow the Stage 1 metric definitions exactly.
--
-- Python (src/run_sql_analysis.py) splits this file on the
-- "-- @block: <name>" markers and executes each block in order through
-- DuckDB. All metric math happens here in SQL; Python only runs the SQL
-- and saves the resulting tables.

-- @block: setup
-- Load the CSV into a view with an explicit column list (no SELECT *)
-- so downstream queries have a stable, typed schema to work against.
CREATE OR REPLACE VIEW ab_test_data AS
SELECT
    user_id,
    variant,
    assignment_date,
    device_type,
    country,
    new_vs_returning_user,
    converted,
    order_revenue,
    had_checkout_error,
    refunded
FROM read_csv_auto('data/ab_test_data.csv', header = true);

-- @block: data_quality
-- Dataset-wide integrity checks: row count, duplicate user IDs, and
-- missing values in every field required by the primary/guardrail metrics.
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT user_id) AS distinct_user_ids,
    COUNT(*) - COUNT(DISTINCT user_id) AS duplicate_user_ids,
    SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) AS missing_user_id,
    SUM(CASE WHEN variant IS NULL THEN 1 ELSE 0 END) AS missing_variant,
    SUM(CASE WHEN assignment_date IS NULL THEN 1 ELSE 0 END) AS missing_assignment_date,
    SUM(CASE WHEN converted IS NULL THEN 1 ELSE 0 END) AS missing_converted,
    SUM(CASE WHEN order_revenue IS NULL THEN 1 ELSE 0 END) AS missing_order_revenue,
    SUM(CASE WHEN had_checkout_error IS NULL THEN 1 ELSE 0 END) AS missing_had_checkout_error,
    SUM(CASE WHEN refunded IS NULL THEN 1 ELSE 0 END) AS missing_refunded
FROM ab_test_data;

-- @block: overall_metrics
-- Assignment split, primary metric, and all three guardrails, one row per
-- variant. Every ratio uses NULLIF to guard against divide-by-zero, and
-- rounding is applied only in the final SELECT (raw sums/ratios stay
-- unrounded through the CTEs).
WITH assignment AS (
    SELECT variant, COUNT(*) AS assigned_users
    FROM ab_test_data
    GROUP BY variant
),
total AS (
    SELECT COUNT(*) AS total_assigned FROM ab_test_data
),
primary_metric AS (
    -- Primary metric: conversion_rate = converted users / eligible users
    -- (eligible = users who started checkout = every row, per Stage 1 s.5).
    SELECT
        variant,
        COUNT(*) AS eligible_users,
        SUM(converted) AS converted_users,
        SUM(converted) * 1.0 / NULLIF(COUNT(*), 0) AS conversion_rate
    FROM ab_test_data
    GROUP BY variant
),
guardrail_aov AS (
    -- AOV = total purchase revenue / completed purchases (purchasers-only
    -- denominator; order_revenue is 0 for non-purchasers so the sum is
    -- already "total purchase revenue").
    SELECT
        variant,
        SUM(order_revenue) * 1.0 / NULLIF(SUM(converted), 0) AS aov
    FROM ab_test_data
    GROUP BY variant
),
guardrail_error AS (
    -- error_rate = sessions with an error / sessions started (all rows).
    SELECT
        variant,
        SUM(had_checkout_error) * 1.0 / NULLIF(COUNT(*), 0) AS checkout_error_rate
    FROM ab_test_data
    GROUP BY variant
),
guardrail_refund AS (
    -- refund_rate = refunded purchases / completed purchases
    -- (purchasers-only denominator, matching Stage 1 s.6).
    SELECT
        variant,
        SUM(refunded) * 1.0 / NULLIF(SUM(converted), 0) AS refund_rate
    FROM ab_test_data
    GROUP BY variant
)
SELECT
    a.variant,
    a.assigned_users,
    ROUND(a.assigned_users * 100.0 / t.total_assigned, 2) AS assignment_pct,
    p.eligible_users,
    p.converted_users,
    ROUND(p.conversion_rate * 100, 2) AS conversion_rate_pct,
    ROUND(g_aov.aov, 2) AS aov,
    ROUND(g_err.checkout_error_rate * 100, 2) AS checkout_error_rate_pct,
    ROUND(g_ref.refund_rate * 100, 2) AS refund_rate_pct
FROM assignment a
CROSS JOIN total t
JOIN primary_metric p ON p.variant = a.variant
JOIN guardrail_aov g_aov ON g_aov.variant = a.variant
JOIN guardrail_error g_err ON g_err.variant = a.variant
JOIN guardrail_refund g_ref ON g_ref.variant = a.variant
ORDER BY a.variant;

-- @block: segment_metrics
-- Conversion and sample size by variant, cut three ways. segment_type
-- labels which cut a row belongs to so all three fit in one table.
SELECT
    'device_type' AS segment_type,
    device_type AS segment_value,
    variant,
    COUNT(*) AS eligible_users,
    SUM(converted) AS converted_users,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) AS conversion_rate_pct
FROM ab_test_data
GROUP BY device_type, variant

UNION ALL

SELECT
    'country' AS segment_type,
    country AS segment_value,
    variant,
    COUNT(*) AS eligible_users,
    SUM(converted) AS converted_users,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) AS conversion_rate_pct
FROM ab_test_data
GROUP BY country, variant

UNION ALL

SELECT
    'new_vs_returning_user' AS segment_type,
    new_vs_returning_user AS segment_value,
    variant,
    COUNT(*) AS eligible_users,
    SUM(converted) AS converted_users,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) AS conversion_rate_pct
FROM ab_test_data
GROUP BY new_vs_returning_user, variant

ORDER BY segment_type, segment_value, variant;

-- @block: daily_metrics
-- Daily conversion by variant plus a running (cumulative) conversion rate,
-- built with a window-function SUM(...) OVER (PARTITION BY variant
-- ORDER BY assignment_date) so the cumulative total re-derives from the
-- daily grain rather than being computed separately.
WITH daily AS (
    SELECT
        variant,
        assignment_date,
        COUNT(*) AS daily_eligible_users,
        SUM(converted) AS daily_converted_users
    FROM ab_test_data
    GROUP BY variant, assignment_date
),
with_cumulative AS (
    SELECT
        variant,
        assignment_date,
        daily_eligible_users,
        daily_converted_users,
        SUM(daily_eligible_users) OVER (
            PARTITION BY variant ORDER BY assignment_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_eligible_users,
        SUM(daily_converted_users) OVER (
            PARTITION BY variant ORDER BY assignment_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_converted_users
    FROM daily
)
SELECT
    variant,
    assignment_date,
    daily_eligible_users,
    daily_converted_users,
    ROUND(daily_converted_users * 100.0 / NULLIF(daily_eligible_users, 0), 2) AS daily_conversion_rate_pct,
    cumulative_eligible_users,
    cumulative_converted_users,
    ROUND(cumulative_converted_users * 100.0 / NULLIF(cumulative_eligible_users, 0), 2) AS cumulative_conversion_rate_pct
FROM with_cumulative
ORDER BY variant, assignment_date;