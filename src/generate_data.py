"""
Generate synthetic checkout A/B test data.

Grain: one row per eligible user (matches the unit of randomization AND the
analysis unit defined in docs/01_experiment_design.md — each user's first
checkout attempt during the 14-day experiment window).

All relationships below (conversion lift, device/returning-user effects,
guardrail distributions) are SIMULATED ASSUMPTIONS for this educational
project, not real business findings. They exist only to give the synthetic
dataset a realistic, testable shape.
"""

from pathlib import Path

import numpy as np
import pandas as pd

# --- Config -------------------------------------------------------------
SEED = 42
N_USERS = 20_000
EXPERIMENT_START = pd.Timestamp("2026-06-01")
EXPERIMENT_DAYS = 14  # matches Stage 1 duration assumption

# Simulated assumption: control baseline conversion rate and the modest
# absolute lift the new checkout gives treatment users.
BASE_CONVERSION_RATE = 0.10
TREATMENT_LIFT = 0.01

# Simulated assumption: small additive effects for realism only, applied
# equally to both variants so they don't interact with the treatment effect.
DEVICE_EFFECT = {"mobile": -0.01, "desktop": 0.01, "tablet": 0.0}
RETURNING_USER_EFFECT = 0.015

# Simulated assumption: guardrail baselines, kept equal across variants
# (any variant-level difference in the output is sampling noise only).
AOV_LOG_MEAN = np.log(75)  # ~$75 typical order
AOV_LOG_SIGMA = 0.4
ERROR_RATE = 0.03
REFUND_RATE = 0.05

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_PATH = DATA_DIR / "ab_test_data.csv"


def generate(rng: np.random.Generator) -> pd.DataFrame:
    user_id = np.arange(1, N_USERS + 1)

    # Unit of randomization: independent 50/50 coin flip per user.
    variant = rng.choice(["control", "treatment"], size=N_USERS, p=[0.5, 0.5])

    # Segmentation columns, drawn independently of variant so they cannot
    # bias the control-vs-treatment comparison.
    day_offset = rng.integers(0, EXPERIMENT_DAYS, size=N_USERS)
    assignment_date = EXPERIMENT_START + pd.to_timedelta(day_offset, unit="D")
    device_type = rng.choice(
        ["mobile", "desktop", "tablet"], size=N_USERS, p=[0.55, 0.35, 0.10]
    )
    country = rng.choice(
        ["US", "UK", "CA", "DE", "IN"], size=N_USERS, p=[0.5, 0.15, 0.15, 0.1, 0.1]
    )
    new_vs_returning_user = rng.choice(
        ["new", "returning"], size=N_USERS, p=[0.6, 0.4]
    )

    # --- Primary metric: conversion -------------------------------------
    conv_prob = np.full(N_USERS, BASE_CONVERSION_RATE)
    conv_prob += np.where(variant == "treatment", TREATMENT_LIFT, 0.0)
    conv_prob += np.vectorize(DEVICE_EFFECT.get)(device_type)
    conv_prob += np.where(new_vs_returning_user == "returning", RETURNING_USER_EFFECT, 0.0)
    conv_prob = np.clip(conv_prob, 0.01, 0.5)
    converted = rng.binomial(1, conv_prob)

    # --- Guardrail: checkout errors (can happen regardless of outcome) --
    had_checkout_error = rng.binomial(1, ERROR_RATE, size=N_USERS)

    # --- Guardrail: order revenue (purchasers only, same distribution
    # for both variants -> any variant gap in the output is noise) -------
    order_revenue = np.zeros(N_USERS)
    n_converted = converted.sum()
    order_revenue[converted == 1] = np.round(
        rng.lognormal(AOV_LOG_MEAN, AOV_LOG_SIGMA, size=n_converted), 2
    )

    # --- Guardrail: refunds (purchasers only, same rate both variants) --
    refunded = np.zeros(N_USERS, dtype=int)
    refunded[converted == 1] = rng.binomial(1, REFUND_RATE, size=n_converted)

    return pd.DataFrame(
        {
            "user_id": user_id,
            "variant": variant,
            "assignment_date": assignment_date,
            "device_type": device_type,
            "country": country,
            "new_vs_returning_user": new_vs_returning_user,
            "converted": converted,
            "order_revenue": order_revenue,
            "had_checkout_error": had_checkout_error,
            "refunded": refunded,
        }
    )


def validate_and_report(df: pd.DataFrame) -> None:
    print("=== Row count ===")
    print(len(df))

    print("\n=== Duplicate user_id count ===")
    print(df["user_id"].duplicated().sum())

    print("\n=== Missing value counts ===")
    print(df.isna().sum())

    print("\n=== Assignment distribution ===")
    print(df["variant"].value_counts())
    print(df["variant"].value_counts(normalize=True))

    print("\n=== Primary metric: conversion rate by variant ===")
    print(df.groupby("variant")["converted"].mean())

    purchasers = df[df["converted"] == 1]

    print("\n=== Guardrail: AOV by variant (purchasers only) ===")
    print(purchasers.groupby("variant")["order_revenue"].mean())

    print("\n=== Guardrail: checkout error rate by variant ===")
    print(df.groupby("variant")["had_checkout_error"].mean())

    print("\n=== Guardrail: refund rate by variant (of purchasers) ===")
    print(purchasers.groupby("variant")["refunded"].mean())


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    df = generate(rng)
    validate_and_report(df)

    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(df)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()