"""Run pairwise tests, effect-size calculations, and multiplicity corrections."""

from __future__ import annotations

from itertools import combinations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import false_discovery_control, fisher_exact, ttest_ind

from common import ALPHA, FIGURES_DIR, MARKETING_DATA, TABLES_DIR, apply_plot_style, ensure_output_directories


def interpret_effect_size(value: float) -> str:
    """Interpret the absolute magnitude of Cohen's d."""

    magnitude = abs(value)
    if magnitude < 0.2:
        return "negligible"
    if magnitude < 0.5:
        return "small"
    if magnitude < 0.8:
        return "medium"
    return "large"


def cohens_d(group_a: np.ndarray, group_b: np.ndarray) -> float:
    """Calculate the lab-specified pooled-SD effect size (B minus A)."""

    pooled_sd = np.sqrt((np.var(group_a, ddof=1) + np.var(group_b, ddof=1)) / 2)
    if pooled_sd == 0 or np.isnan(pooled_sd):
        return np.nan
    return float((np.mean(group_b) - np.mean(group_a)) / pooled_sd)


def cpa_pairwise_tests(data: pd.DataFrame) -> pd.DataFrame:
    """Use Welch independent t-tests to compare daily CPA distributions."""

    rows: list[dict] = []
    channels = sorted(data["channel"].unique())
    for channel_a, channel_b in combinations(channels, 2):
        a = data.loc[data["channel"].eq(channel_a), "cpa"].replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
        b = data.loc[data["channel"].eq(channel_b), "cpa"].replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
        result = ttest_ind(a, b, equal_var=False, nan_policy="omit")
        mean_a = float(np.mean(a))
        mean_b = float(np.mean(b))
        difference = mean_b - mean_a
        effect = cohens_d(a, b)
        rows.append(
            {
                "metric": "daily_cpa",
                "channel_a": channel_a,
                "channel_b": channel_b,
                "n_a": len(a),
                "n_b": len(b),
                "mean_a": mean_a,
                "mean_b": mean_b,
                "difference_b_minus_a": difference,
                "percent_difference_vs_a": difference / mean_a if mean_a else np.nan,
                "t_statistic": float(result.statistic),
                "p_value": float(result.pvalue),
                "cohens_d": effect,
                "effect_size": interpret_effect_size(effect),
                "significant_uncorrected": bool(result.pvalue < ALPHA),
            }
        )
    return pd.DataFrame(rows)


def fisher_conversion_tests(data: pd.DataFrame) -> pd.DataFrame:
    """Compare aggregated conversion counts with two-sided Fisher exact tests."""

    totals = data.groupby("channel", as_index=False).agg(clicks=("clicks", "sum"), conversions=("conversions", "sum"))
    totals["non_conversions"] = totals["clicks"] - totals["conversions"]
    lookup = totals.set_index("channel")

    rows: list[dict] = []
    channels = sorted(lookup.index)
    for channel_a, channel_b in combinations(channels, 2):
        a = lookup.loc[channel_a]
        b = lookup.loc[channel_b]
        contingency = np.array(
            [
                [int(a["conversions"]), int(a["non_conversions"])],
                [int(b["conversions"]), int(b["non_conversions"])],
            ]
        )
        result = fisher_exact(contingency, alternative="two-sided")
        rate_a = a["conversions"] / a["clicks"]
        rate_b = b["conversions"] / b["clicks"]
        rows.append(
            {
                "metric": "conversion_rate",
                "channel_a": channel_a,
                "channel_b": channel_b,
                "conversions_a": int(a["conversions"]),
                "clicks_a": int(a["clicks"]),
                "conversions_b": int(b["conversions"]),
                "clicks_b": int(b["clicks"]),
                "rate_a": rate_a,
                "rate_b": rate_b,
                "difference_b_minus_a": rate_b - rate_a,
                "percent_difference_vs_a": (rate_b - rate_a) / rate_a if rate_a else np.nan,
                "odds_ratio": float(result.statistic),
                "p_value": float(result.pvalue),
                "significant_uncorrected": bool(result.pvalue < ALPHA),
            }
        )
    return pd.DataFrame(rows)


def apply_corrections(results: pd.DataFrame) -> pd.DataFrame:
    """Add Bonferroni and Benjamini-Hochberg adjusted decisions."""

    corrected = results.copy()
    number_of_tests = len(corrected)
    corrected["bonferroni_alpha"] = ALPHA / number_of_tests
    corrected["p_value_bonferroni"] = np.minimum(corrected["p_value"] * number_of_tests, 1.0)
    corrected["significant_bonferroni"] = corrected["p_value"] < corrected["bonferroni_alpha"]
    corrected["p_value_fdr"] = false_discovery_control(corrected["p_value"].to_numpy(), method="bh")
    corrected["significant_fdr"] = corrected["p_value_fdr"] < ALPHA
    return corrected


def correction_summary(cpa: pd.DataFrame, conversion: pd.DataFrame) -> pd.DataFrame:
    """Summarize how correction changes the discovery count."""

    rows = []
    for label, frame in (("CPA t-tests", cpa), ("Conversion Fisher tests", conversion)):
        rows.extend(
            [
                {"test_family": label, "method": "Uncorrected", "significant_comparisons": int(frame["significant_uncorrected"].sum()), "total_comparisons": len(frame)},
                {"test_family": label, "method": "Bonferroni", "significant_comparisons": int(frame["significant_bonferroni"].sum()), "total_comparisons": len(frame)},
                {"test_family": label, "method": "Benjamini-Hochberg FDR", "significant_comparisons": int(frame["significant_fdr"].sum()), "total_comparisons": len(frame)},
            ]
        )
    return pd.DataFrame(rows)


def plot_cpa_heatmap(cpa: pd.DataFrame) -> None:
    """Create a symmetric heatmap of raw pairwise CPA p-values."""

    apply_plot_style()
    channels = sorted(set(cpa["channel_a"]).union(cpa["channel_b"]))
    matrix = pd.DataFrame(np.ones((len(channels), len(channels))), index=channels, columns=channels)
    annotations = pd.DataFrame("1.000", index=channels, columns=channels)
    for row in cpa.itertuples(index=False):
        matrix.loc[row.channel_a, row.channel_b] = row.p_value
        matrix.loc[row.channel_b, row.channel_a] = row.p_value
        label = f"{row.p_value:.3g}" + ("*" if row.significant_fdr else "")
        annotations.loc[row.channel_a, row.channel_b] = label
        annotations.loc[row.channel_b, row.channel_a] = label

    fig, ax = plt.subplots(figsize=(10, 8), constrained_layout=True)
    sns.heatmap(
        matrix,
        annot=annotations,
        fmt="",
        cmap="RdYlGn",
        vmin=0,
        vmax=0.10,
        linewidths=0.7,
        linecolor="white",
        cbar_kws={"label": "Raw p-value (green = larger)"},
        ax=ax,
    )
    ax.set_title("Pairwise daily CPA tests — raw p-values\n* remains significant after FDR correction")
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.savefig(FIGURES_DIR / "metric_comparison_heatmap.png", bbox_inches="tight")
    plt.close(fig)


def plot_conversion_rates(data: pd.DataFrame) -> None:
    """Plot weighted conversion rates based on total clicks and conversions."""

    apply_plot_style()
    totals = data.groupby("channel", as_index=False).agg(clicks=("clicks", "sum"), conversions=("conversions", "sum"))
    totals["conversion_rate"] = totals["conversions"] / totals["clicks"]
    totals = totals.sort_values("conversion_rate", ascending=True)
    colors = ["#0F766E" if channel == "Referral" else "#94A3B8" for channel in totals["channel"]]

    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    bars = ax.barh(totals["channel"], totals["conversion_rate"], color=colors)
    ax.xaxis.set_major_formatter(plt.matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title("Referral leads weighted conversion rate")
    ax.set_xlabel("Conversions / clicks")
    ax.grid(axis="x", alpha=0.25)
    ax.grid(axis="y", visible=False)
    for bar, value in zip(bars, totals["conversion_rate"]):
        ax.text(bar.get_width() + 0.0003, bar.get_y() + bar.get_height() / 2, f"{value:.2%}", va="center", fontsize=9)
    fig.savefig(FIGURES_DIR / "rate_comparison.png", bbox_inches="tight")
    plt.close(fig)


def plot_correction_comparison(summary: pd.DataFrame) -> None:
    """Visualize discovery counts before and after multiplicity correction."""

    apply_plot_style()
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    sns.barplot(
        data=summary,
        x="method",
        y="significant_comparisons",
        hue="test_family",
        palette=["#0F766E", "#64748B"],
        ax=ax,
    )
    ax.set_title("Sensitivity of significant comparison counts to multiplicity correction")
    ax.set_xlabel("")
    ax.set_ylabel("Significant pairwise comparisons")
    ax.legend(title="", loc="lower right")
    ax.grid(axis="y", alpha=0.25)
    ax.grid(axis="x", visible=False)
    for container in ax.containers:
        ax.bar_label(container, fmt="%.0f", padding=3)
    fig.savefig(FIGURES_DIR / "correction_comparison.png", bbox_inches="tight")
    plt.close(fig)


def main() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run Parts 2-3 and return corrected result tables."""

    ensure_output_directories()
    data = pd.read_csv(MARKETING_DATA, parse_dates=["date"])
    cpa = apply_corrections(cpa_pairwise_tests(data))
    conversion = apply_corrections(fisher_conversion_tests(data))
    summary = correction_summary(cpa, conversion)

    cpa.to_csv(TABLES_DIR / "cpa_pairwise_results.csv", index=False)
    conversion.to_csv(TABLES_DIR / "fisher_conversion_results.csv", index=False)
    summary.to_csv(TABLES_DIR / "correction_summary.csv", index=False)

    plot_cpa_heatmap(cpa)
    plot_conversion_rates(data)
    plot_correction_comparison(summary)

    expected_false_positives = (len(cpa) + len(conversion)) * ALPHA
    print(f"Ran {len(cpa)} CPA tests and {len(conversion)} Fisher tests.")
    print(f"At alpha={ALPHA:.2f}, {expected_false_positives:.1f} false positives are expected by chance across all tests under the global null.")
    print(summary.to_string(index=False))
    return cpa, conversion, summary


if __name__ == "__main__":
    main()
