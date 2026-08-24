"""Estimate statistical power and future sample-size needs for CPA tests."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind

from common import ALPHA, FIGURES_DIR, RANDOM_SEED, TABLES_DIR, apply_plot_style, ensure_output_directories


def empirical_power_cpa(
    true_diff_pct: float,
    base_cpa: float,
    n_days: int,
    n_sim: int = 1000,
    alpha: float = ALPHA,
    seed: int = RANDOM_SEED,
) -> float:
    """Vectorized Monte Carlo power for a two-sided Welch CPA t-test."""

    rng = np.random.default_rng(seed)
    standard_deviation = base_cpa * 0.15
    group_a = rng.normal(base_cpa, standard_deviation, size=(n_sim, n_days))
    group_b = rng.normal(base_cpa * (1 + true_diff_pct), standard_deviation, size=(n_sim, n_days))
    group_a = np.clip(group_a, base_cpa * 0.50, None)
    group_b = np.clip(group_b, base_cpa * 0.50, None)
    p_values = ttest_ind(group_a, group_b, axis=1, equal_var=False).pvalue
    return float(np.mean(p_values < alpha))


def build_power_grid(base_cpa: float = 800.0) -> pd.DataFrame:
    """Calculate the lab-requested effect-size and sample-size grid."""

    rows = []
    for effect_index, effect in enumerate((0.05, 0.10, 0.15, 0.20)):
        for sample_index, days in enumerate((30, 60, 90, 120, 180)):
            rows.append(
                {
                    "effect_size_pct": effect,
                    "n_days_per_channel": days,
                    "power": empirical_power_cpa(effect, base_cpa, days, seed=RANDOM_SEED + effect_index * 100 + sample_index),
                }
            )
    return pd.DataFrame(rows)


def minimum_sample_sizes(base_cpa: float = 800.0, target_power: float = 0.80) -> pd.DataFrame:
    """Find the smallest simulated day count that reaches target power."""

    search_days = list(range(20, 201, 5)) + [240, 300, 365]
    rows = []
    for effect_index, effect in enumerate((0.05, 0.10, 0.15, 0.20)):
        minimum = None
        achieved_power = None
        for sample_index, days in enumerate(search_days):
            power = empirical_power_cpa(
                effect,
                base_cpa,
                days,
                seed=RANDOM_SEED + 1000 + effect_index * 200 + sample_index,
            )
            if power >= target_power:
                minimum = days
                achieved_power = power
                break
        rows.append(
            {
                "effect_size_pct": effect,
                "target_power": target_power,
                "minimum_days_per_channel": minimum if minimum is not None else ">365",
                "power_at_minimum": achieved_power,
                "current_90_days_status": "sufficient" if isinstance(minimum, int) and minimum <= 90 else "insufficient",
            }
        )
    return pd.DataFrame(rows)


def assess_current_significant_pairs(cpa_results: pd.DataFrame) -> pd.DataFrame:
    """Assess empirical power for CPA pairs that survive FDR correction."""

    rows = []
    significant = cpa_results.loc[cpa_results["significant_fdr"]].copy()
    for pair_index, row in significant.reset_index(drop=True).iterrows():
        baseline = min(row["mean_a"], row["mean_b"])
        effect = abs(row["mean_b"] - row["mean_a"]) / baseline
        current_power = empirical_power_cpa(effect, baseline, 90, seed=RANDOM_SEED + 5000 + pair_index)
        days_needed: int | str = 90
        if current_power < 0.80:
            days_needed = ">365"
            for sample_index, days in enumerate(list(range(95, 201, 5)) + [240, 300, 365]):
                candidate_power = empirical_power_cpa(
                    effect,
                    baseline,
                    days,
                    seed=RANDOM_SEED + 6000 + pair_index * 100 + sample_index,
                )
                if candidate_power >= 0.80:
                    days_needed = days
                    break
        rows.append(
            {
                "channel_a": row["channel_a"],
                "channel_b": row["channel_b"],
                "observed_difference_pct": effect,
                "power_with_90_days": current_power,
                "estimated_days_for_80pct_power": days_needed,
            }
        )
    return pd.DataFrame(rows)


def plot_power_curves(power_grid: pd.DataFrame) -> None:
    """Plot empirical power curves for four practically meaningful effects."""

    apply_plot_style()
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for effect, group in power_grid.groupby("effect_size_pct"):
        ax.plot(
            group["n_days_per_channel"],
            group["power"],
            marker="o",
            linewidth=2,
            label=f"{effect:.0%} CPA difference",
        )
    ax.axhline(0.80, color="#DC2626", linestyle="--", linewidth=1.2, label="80% target")
    ax.set_ylim(0, 1.03)
    ax.yaxis.set_major_formatter(plt.matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title("Small CPA differences require substantially more observation days")
    ax.set_xlabel("Days per channel")
    ax.set_ylabel("Empirical power")
    ax.legend(ncol=2)
    ax.grid(alpha=0.25)
    fig.savefig(FIGURES_DIR / "power_analysis_cpa.png", bbox_inches="tight")
    plt.close(fig)


def main() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run Part 4 and return power outputs."""

    ensure_output_directories()
    power_grid = build_power_grid()
    minimum_sizes = minimum_sample_sizes()
    cpa_results = pd.read_csv(TABLES_DIR / "cpa_pairwise_results.csv")
    current_adequacy = assess_current_significant_pairs(cpa_results)

    power_grid.to_csv(TABLES_DIR / "power_analysis_results.csv", index=False)
    minimum_sizes.to_csv(TABLES_DIR / "sample_size_recommendations.csv", index=False)
    current_adequacy.to_csv(TABLES_DIR / "current_data_adequacy.csv", index=False)
    plot_power_curves(power_grid)

    print("\nMinimum sample-size recommendations:")
    print(minimum_sizes.to_string(index=False))
    return power_grid, minimum_sizes, current_adequacy


if __name__ == "__main__":
    main()
