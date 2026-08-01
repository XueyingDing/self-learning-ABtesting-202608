"""
Stage 5: visualization and analytical storytelling for the checkout A/B test.

This script does NOT compute any new hypothesis test, does NOT touch the
random seed, and does NOT regenerate data. It only reads the existing Stage
3/4 outputs (outputs/sql/*.csv, outputs/statistics/*.csv) and renders them.

The one exception: per-variant 95% confidence intervals for the primary
chart are not in outputs/statistics/test_results.csv (that file only has the
CI for the DIFFERENCE between variants). Those individual-variant CIs are a
standard descriptive interval (Wald normal-approximation, same alpha=0.05
already used in Stage 4) computed here from the counts already in
outputs/sql/overall_metrics.csv -- not a new significance test.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT_DIR = Path(__file__).resolve().parent.parent
SQL_OUT_DIR = ROOT_DIR / "outputs" / "sql"
STATS_OUT_DIR = ROOT_DIR / "outputs" / "statistics"
FIG_DIR = ROOT_DIR / "outputs" / "figures"

ALPHA = 0.05  # matches docs/01_experiment_design.md / Stage 4, not a new choice

# Fixed categorical color assignment -- Okabe-Ito colorblind-safe pair.
# Control and treatment ALWAYS get these colors, in every figure.
COLOR_CONTROL = "#0072B2"
COLOR_TREATMENT = "#D55E00"
GRID_COLOR = "#dddddd"


def load_data():
    overall = pd.read_csv(SQL_OUT_DIR / "overall_metrics.csv")
    segment = pd.read_csv(SQL_OUT_DIR / "segment_metrics.csv")
    daily = pd.read_csv(SQL_OUT_DIR / "daily_metrics.csv", parse_dates=["assignment_date"])
    test_results = pd.read_csv(STATS_OUT_DIR / "test_results.csv")
    return overall, segment, daily, test_results


def style_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------
# A. Primary conversion chart
# ---------------------------------------------------------------------
def plot_conversion_ci(overall: pd.DataFrame, test_results: pd.DataFrame, out_path: Path):
    control = overall[overall["variant"] == "control"].iloc[0]
    treatment = overall[overall["variant"] == "treatment"].iloc[0]

    n_c, x_c = control["eligible_users"], control["converted_users"]
    n_t, x_t = treatment["eligible_users"], treatment["converted_users"]
    p_c, p_t = x_c / n_c, x_t / n_t

    # Per-variant Wald 95% CI (descriptive interval, not a hypothesis test).
    z_crit = stats.norm.ppf(1 - ALPHA / 2)
    se_c = np.sqrt(p_c * (1 - p_c) / n_c)
    se_t = np.sqrt(p_t * (1 - p_t) / n_t)
    ci_c = (p_c - z_crit * se_c, p_c + z_crit * se_c)
    ci_t = (p_t - z_crit * se_t, p_t + z_crit * se_t)

    primary_row = test_results[test_results["test_id"] == "B_primary"].iloc[0]
    abs_lift_pp = primary_row["absolute_diff"] * 100
    p_value = primary_row["p_value_raw"]

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    x_pos = [0, 1]
    rates_pct = [p_c * 100, p_t * 100]
    err_low = [(p_c - ci_c[0]) * 100, (p_t - ci_t[0]) * 100]
    err_high = [(ci_c[1] - p_c) * 100, (ci_t[1] - p_t) * 100]
    colors = [COLOR_CONTROL, COLOR_TREATMENT]

    ax.bar(x_pos, rates_pct, width=0.5, color=colors, zorder=3)
    ax.errorbar(
        x_pos, rates_pct, yerr=[err_low, err_high],
        fmt="none", ecolor="black", elinewidth=1.5, capsize=6, zorder=4,
    )

    ax.set_xticks(x_pos)
    ax.set_xticklabels([
        f"Control\n(n={n_c:,})",
        f"Treatment\n(n={n_t:,})",
    ])
    ax.set_ylabel("Conversion rate (%)")
    ax.set_title("Primary Metric: Purchase Conversion Rate by Variant")
    style_axis(ax)

    for xi, rate in zip(x_pos, rates_pct):
        ax.text(xi, rate + 0.5, f"{rate:.2f}%", ha="center", va="bottom", fontweight="bold")

    # Lift annotation bracket between the two bars.
    bracket_y = max(ci_c[1], ci_t[1]) * 100 + 1.8
    ax.plot([0, 0, 1, 1], [bracket_y - 0.3, bracket_y, bracket_y, bracket_y - 0.3], color="black", linewidth=1)
    ax.text(0.5, bracket_y + 0.2, f"Observed absolute lift: +{abs_lift_pp:.2f}pp",
            ha="center", va="bottom", fontweight="bold")
    ax.set_ylim(0, bracket_y + 2.2)

    fig.text(
        0.5, -0.02,
        f"Error bars = 95% CI for each variant's own rate.\n"
        f"Significance comes from the two-sample proportion z-test (p={p_value:.1e}), "
        "not from visually comparing whether these CIs overlap.",
        ha="center", va="top", fontsize=8.5, color="#444444", wrap=True,
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------
# B. Daily experiment trend
# ---------------------------------------------------------------------
def plot_daily_trend(daily: pd.DataFrame, out_path: Path):
    fig, (ax_daily, ax_cum) = plt.subplots(2, 1, figsize=(9, 8), sharex=True)

    for variant, color in [("control", COLOR_CONTROL), ("treatment", COLOR_TREATMENT)]:
        d = daily[daily["variant"] == variant].sort_values("assignment_date")
        ax_daily.plot(
            d["assignment_date"], d["daily_conversion_rate_pct"],
            marker="o", markersize=4, linewidth=1.5, color=color, label=variant.capitalize(),
        )
        ax_cum.plot(
            d["assignment_date"], d["cumulative_conversion_rate_pct"],
            marker="o", markersize=4, linewidth=2, color=color, label=variant.capitalize(),
        )

    ax_daily.set_title("Daily Conversion Rate by Variant")
    ax_daily.set_ylabel("Daily rate (%)")
    ax_daily.legend(frameon=False)
    style_axis(ax_daily)

    ax_cum.set_title("Cumulative Conversion Rate by Variant")
    ax_cum.set_ylabel("Cumulative rate (%)")
    ax_cum.set_xlabel("Assignment date")
    ax_cum.legend(frameon=False)
    style_axis(ax_cum)
    fig.autofmt_xdate()

    fig.text(
        0.5, -0.01,
        "Top panel: single-day rates (noisy, day-to-day). Bottom panel: running "
        "cumulative rate (smooths toward the overall result). No daily significance "
        "tests are shown -- use the top panel only to check whether the overall gap "
        "is driven by one unusual date.",
        ha="center", va="top", fontsize=8.5, color="#444444", wrap=True,
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------
# C. Segment conversion chart
# ---------------------------------------------------------------------
def plot_segment_conversion(segment: pd.DataFrame, out_path: Path):
    segment_types = ["device_type", "country", "new_vs_returning_user"]
    titles = {
        "device_type": "By Device Type",
        "country": "By Country",
        "new_vs_returning_user": "By New vs. Returning",
    }

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))

    for ax, seg_type in zip(axes, segment_types):
        sub = segment[segment["segment_type"] == seg_type]
        values = sorted(sub["segment_value"].unique())
        x = np.arange(len(values))
        width = 0.38

        control_rates = [sub[(sub["segment_value"] == v) & (sub["variant"] == "control")]["conversion_rate_pct"].iloc[0] for v in values]
        treatment_rates = [sub[(sub["segment_value"] == v) & (sub["variant"] == "treatment")]["conversion_rate_pct"].iloc[0] for v in values]
        control_n = [sub[(sub["segment_value"] == v) & (sub["variant"] == "control")]["eligible_users"].iloc[0] for v in values]
        treatment_n = [sub[(sub["segment_value"] == v) & (sub["variant"] == "treatment")]["eligible_users"].iloc[0] for v in values]

        bars_c = ax.bar(x - width / 2, control_rates, width, color=COLOR_CONTROL, label="Control", zorder=3)
        bars_t = ax.bar(x + width / 2, treatment_rates, width, color=COLOR_TREATMENT, label="Treatment", zorder=3)

        for bar, n in zip(bars_c, control_n):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
                    f"n={n:,}", ha="center", va="bottom", fontsize=6.5, rotation=90)
        for bar, n in zip(bars_t, treatment_n):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
                    f"n={n:,}", ha="center", va="bottom", fontsize=6.5, rotation=90)

        ax.set_xticks(x)
        ax.set_xticklabels(values, rotation=0 if seg_type != "country" else 0)
        ax.set_title(titles[seg_type], fontsize=11)
        ax.set_ylabel("Conversion rate (%)")
        style_axis(ax)
        ax.set_ylim(0, max(control_rates + treatment_rates) + 4)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.05))
    fig.suptitle("Conversion Rate by Segment (Exploratory, Descriptive Only)", y=1.12, fontsize=13)

    fig.text(
        0.5, -0.05,
        "Exploratory descriptive comparisons only. No significance testing was performed at the "
        "segment level, and no claim of treatment-effect heterogeneity is made -- bar-height "
        "differences here may be sampling noise, not a real interaction with variant.",
        ha="center", va="top", fontsize=8.5, color="#444444", wrap=True,
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------
# D. Guardrail chart
# ---------------------------------------------------------------------
def plot_guardrails(test_results: pd.DataFrame, out_path: Path):
    specs = [
        ("C1_error_rate", "Checkout Error Rate", "%", 100),
        ("C2_refund_rate", "Refund Rate", "%", 100),
        ("C3_aov", "Average Order Value", "$", 1),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 5.5))

    for ax, (test_id, title, unit, scale) in zip(axes, specs):
        row = test_results[test_results["test_id"] == test_id].iloc[0]
        control_val = row["group_a_value"] * scale
        treatment_val = row["group_b_value"] * scale
        holm_p = row["p_value_holm_adjusted"]

        bars = ax.bar([0, 1], [control_val, treatment_val],
                      width=0.5, color=[COLOR_CONTROL, COLOR_TREATMENT], zorder=3)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Control", "Treatment"])
        label_fmt = "{:.2f}%" if unit == "%" else "${:.2f}"
        for bar, val in zip(bars, [control_val, treatment_val]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    label_fmt.format(val), ha="center", va="bottom", fontweight="bold")

        ax.set_title(f"{title}\n(Holm-adjusted p = {holm_p:.2f}, not significant)", fontsize=10)
        ax.set_ylabel(f"{title} ({unit})")
        style_axis(ax)
        ax.set_ylim(0, max(control_val, treatment_val) * 1.25)

    fig.suptitle("Guardrail Metrics by Variant", y=1.04, fontsize=13)
    fig.text(
        0.5, -0.06,
        "None of the three guardrails were statistically significant after Holm correction across "
        "the guardrail family. This does NOT prove the metrics are identical or that there is no "
        "harm -- it means this dataset did not detect a guardrail regression. Refund rate and AOV "
        "are computed over purchasers only (Stage 1 definition); checkout error rate uses all "
        "checkout sessions started.",
        ha="center", va="top", fontsize=8.5, color="#444444", wrap=True,
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    overall, segment, daily, test_results = load_data()

    plot_conversion_ci(overall, test_results, FIG_DIR / "conversion_rate_ci.png")
    print(f"Saved {FIG_DIR / 'conversion_rate_ci.png'}")

    plot_daily_trend(daily, FIG_DIR / "daily_conversion.png")
    print(f"Saved {FIG_DIR / 'daily_conversion.png'}")

    plot_segment_conversion(segment, FIG_DIR / "segment_conversion.png")
    print(f"Saved {FIG_DIR / 'segment_conversion.png'}")

    plot_guardrails(test_results, FIG_DIR / "guardrail_metrics.png")
    print(f"Saved {FIG_DIR / 'guardrail_metrics.png'}")


if __name__ == "__main__":
    main()