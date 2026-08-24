"""Create confidence intervals, a constrained budget allocation, and the memo."""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import (
    MARKETING_DATA,
    MONTHLY_BUDGET_USD,
    PROJECT_ROOT,
    RANDOM_SEED,
    TABLES_DIR,
    ensure_output_directories,
)


def bootstrap_ci(data: np.ndarray, n_bootstrap: int = 2000, ci_level: float = 0.95, seed: int = RANDOM_SEED) -> tuple[float, float]:
    """Return a percentile bootstrap interval for the sample mean."""

    values = np.asarray(data, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(n_bootstrap, len(values)), replace=True)
    bootstrap_means = samples.mean(axis=1)
    alpha = 1 - ci_level
    return tuple(np.quantile(bootstrap_means, [alpha / 2, 1 - alpha / 2]))


def cpa_confidence_intervals(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate 95% CIs for the daily mean CPA of each channel."""

    rows = []
    for index, (channel, group) in enumerate(data.groupby("channel")):
        values = group["cpa"].replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
        lower, upper = bootstrap_ci(values, seed=RANDOM_SEED + index)
        rows.append(
            {
                "channel": channel,
                "valid_days": len(values),
                "mean_daily_cpa": np.mean(values),
                "ci_95_lower": lower,
                "ci_95_upper": upper,
            }
        )
    return pd.DataFrame(rows).sort_values("mean_daily_cpa").reset_index(drop=True)


def bounded_score_allocation(scores: np.ndarray, floor: float = 0.05, cap: float = 0.30) -> np.ndarray:
    """Convert scores to shares subject to a floor and cap using water filling."""

    scores = np.asarray(scores, dtype=float)
    if np.any(scores < 0) or scores.sum() <= 0:
        raise ValueError("Allocation scores must be non-negative and sum to more than zero.")
    number_of_channels = len(scores)
    if floor * number_of_channels > 1 or cap * number_of_channels < 1:
        raise ValueError("Infeasible allocation bounds.")

    shares = np.full(number_of_channels, floor, dtype=float)
    remaining = 1 - shares.sum()
    active = set(range(number_of_channels))
    while active and remaining > 1e-12:
        active_indices = np.array(sorted(active))
        active_scores = scores[active_indices]
        if active_scores.sum() == 0:
            proposals = np.full(len(active_indices), remaining / len(active_indices))
        else:
            proposals = remaining * active_scores / active_scores.sum()
        capped_any = False
        for idx, proposal in zip(active_indices, proposals):
            available = cap - shares[idx]
            if proposal >= available - 1e-12:
                shares[idx] += max(available, 0)
                remaining -= max(available, 0)
                active.remove(int(idx))
                capped_any = True
        if not capped_any:
            shares[active_indices] += proposals
            remaining = 0

    return shares / shares.sum()


def create_budget_allocation(summary: pd.DataFrame) -> pd.DataFrame:
    """Rank channels on efficiency and allocate a constrained $500K budget."""

    allocation = summary[["channel", "conversion_rate", "cpa", "roas", "profit"]].copy()
    channel_count = len(allocation)
    allocation["roas_rank"] = allocation["roas"].rank(ascending=False, method="min")
    allocation["conversion_rank"] = allocation["conversion_rate"].rank(ascending=False, method="min")
    allocation["cpa_rank"] = allocation["cpa"].rank(ascending=True, method="min")
    allocation["roas_points"] = channel_count + 1 - allocation["roas_rank"]
    allocation["conversion_points"] = channel_count + 1 - allocation["conversion_rank"]
    allocation["cpa_points"] = channel_count + 1 - allocation["cpa_rank"]
    allocation["composite_score"] = (
        0.50 * allocation["roas_points"]
        + 0.30 * allocation["conversion_points"]
        + 0.20 * allocation["cpa_points"]
    )
    allocation["recommended_share"] = bounded_score_allocation(allocation["composite_score"].to_numpy())
    allocation["recommended_budget_usd"] = (allocation["recommended_share"] * MONTHLY_BUDGET_USD / 100).round() * 100
    rounding_difference = MONTHLY_BUDGET_USD - allocation["recommended_budget_usd"].sum()
    allocation.loc[allocation["composite_score"].idxmax(), "recommended_budget_usd"] += rounding_difference
    allocation["recommended_share"] = allocation["recommended_budget_usd"] / MONTHLY_BUDGET_USD
    allocation["allocation_guardrail"] = np.select(
        [allocation["recommended_share"].eq(0.30), allocation["recommended_share"].eq(0.05)],
        ["30% maximum", "5% learning floor"],
        default="score-weighted",
    )
    return allocation.sort_values("recommended_budget_usd", ascending=False).reset_index(drop=True)


def significant_findings(cpa: pd.DataFrame, conversion: pd.DataFrame) -> pd.DataFrame:
    """Compile only FDR-robust findings for the business memo."""

    rows = []
    for row in cpa.loc[cpa["significant_fdr"]].itertuples(index=False):
        better = row.channel_a if row.mean_a < row.mean_b else row.channel_b
        rows.append(
            {
                "test_family": "CPA Welch t-test",
                "channel_a": row.channel_a,
                "channel_b": row.channel_b,
                "better_channel": better,
                "absolute_difference": abs(row.difference_b_minus_a),
                "effect_size_or_odds_ratio": row.cohens_d,
                "adjusted_p_value": row.p_value_fdr,
            }
        )
    for row in conversion.loc[conversion["significant_fdr"]].itertuples(index=False):
        better = row.channel_a if row.rate_a > row.rate_b else row.channel_b
        rows.append(
            {
                "test_family": "Conversion Fisher exact test",
                "channel_a": row.channel_a,
                "channel_b": row.channel_b,
                "better_channel": better,
                "absolute_difference": abs(row.difference_b_minus_a),
                "effect_size_or_odds_ratio": row.odds_ratio,
                "adjusted_p_value": row.p_value_fdr,
            }
        )
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame, columns: list[str], formats: dict[str, str]) -> str:
    """Create a small Markdown table without requiring optional dependencies."""

    headers = columns
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in frame[columns].itertuples(index=False, name=None):
        rendered = []
        for column, value in zip(columns, row):
            if column in formats and pd.notna(value):
                rendered.append(formats[column].format(value))
            else:
                rendered.append(str(value))
        lines.append("| " + " | ".join(rendered) + " |")
    return "\n".join(lines)


def write_executive_memo(
    summary: pd.DataFrame,
    cpa: pd.DataFrame,
    conversion: pd.DataFrame,
    intervals: pd.DataFrame,
    allocation: pd.DataFrame,
    sample_sizes: pd.DataFrame,
) -> None:
    """Generate an evidence-linked executive memo from the computed outputs."""

    top = summary.sort_values("roas", ascending=False).iloc[0]
    runner_up = summary.sort_values("roas", ascending=False).iloc[1]
    worst = summary.sort_values("roas", ascending=True).iloc[0]
    cpa_counts = (int(cpa["significant_uncorrected"].sum()), int(cpa["significant_bonferroni"].sum()), int(cpa["significant_fdr"].sum()))
    conversion_counts = (
        int(conversion["significant_uncorrected"].sum()),
        int(conversion["significant_bonferroni"].sum()),
        int(conversion["significant_fdr"].sum()),
    )
    ten_pct_row = sample_sizes.loc[np.isclose(sample_sizes["effect_size_pct"], 0.10)].iloc[0]
    fifteen_pct_row = sample_sizes.loc[np.isclose(sample_sizes["effect_size_pct"], 0.15)].iloc[0]

    allocation_table = markdown_table(
        allocation,
        ["channel", "recommended_share", "recommended_budget_usd", "allocation_guardrail"],
        {"recommended_share": "{:.1%}", "recommended_budget_usd": "${:,.0f}"},
    )
    interval_table = markdown_table(
        intervals,
        ["channel", "mean_daily_cpa", "ci_95_lower", "ci_95_upper", "valid_days"],
        {"mean_daily_cpa": "${:,.0f}", "ci_95_lower": "${:,.0f}", "ci_95_upper": "${:,.0f}", "valid_days": "{:,.0f}"},
    )

    memo = f"""# Executive Memo: Seven-Channel Marketing Budget Allocation

**Date:** 24 August 2026  
**Analyst:** Elza Paegle  
**Decision:** Allocation of a $500,000 monthly marketing budget  
**Dataset:** Solstice SaaS Growth Pack, channel performance sample  
**Period:** 1 January–31 March 2026 (90 days; seven channels; six synthetic companies aggregated by day)

## Executive summary

The evidence supports a controlled shift toward **{top['channel']}**, not an unconstrained reallocation. It delivered the strongest aggregate ROAS ({top['roas']:.2f}x), lowest aggregate CPA (${top['cpa']:,.0f}), and highest weighted conversion rate ({top['conversion_rate']:.2%}); by comparison, the next-best ROAS was only {runner_up['roas']:.2f}x and {worst['channel']} produced the weakest ROAS ({worst['roas']:.2f}x). Pairwise testing confirms that many differences are larger than sampling noise even after multiplicity control. However, the source is a transparent synthetic benchmark rather than observed company data, attribution is not causal, daily observations may be autocorrelated, and cost or demand can change when spend scales. I therefore recommend a **30% cap** on {top['channel']}, a **5% learning floor** for every channel, and staged reallocation using the table below. Release the next budget step only after a live four-week geo- or audience-level holdout confirms incremental profit.

## Key findings

- **CPA tests:** {cpa_counts[0]} of 21 pairs were significant before correction, {cpa_counts[1]} after Bonferroni, and {cpa_counts[2]} after Benjamini–Hochberg FDR.
- **Conversion tests:** {conversion_counts[0]} of 21 pairs were significant before correction, {conversion_counts[1]} after Bonferroni, and {conversion_counts[2]} after FDR.
- **Portfolio economics:** {top['channel']} generated ${top['profit']:,.0f} in attributed profit in the benchmark; the other channels should be treated as learning or upper-funnel investments until incrementality is demonstrated.
- **Power:** approximately {ten_pct_row['minimum_days_per_channel']} days per channel are required to detect a 10% CPA difference with 80% power under the simulation assumptions; a 15% effect requires about {fifteen_pct_row['minimum_days_per_channel']} days. The current 90-day window is sufficient for simulated effects of 10% or more, but not for a subtle 5% difference.
- **Multiplicity choice:** FDR is the main decision rule because the objective is to prioritize promising channels while controlling the expected proportion of false discoveries; Bonferroni is retained as a conservative sensitivity check.

## Recommended monthly allocation

The score weights ROAS at 50%, conversion rate at 30%, and CPA at 20%. Shares are bounded between 5% and 30% to limit model and concentration risk.

{allocation_table}

## Daily CPA uncertainty

The intervals below are non-parametric 95% percentile bootstrap intervals for mean daily CPA, using only days with at least one conversion.

{interval_table}

## Statistical caveats

1. **Synthetic benchmark:** The Hugging Face source is public and well documented but contains simulated SaaS companies, not this firm's transactions. It is appropriate for demonstrating the workflow, not for claiming realized lift.
2. **Observational attribution:** ROAS and profit are attributed, not incremental. Cross-channel spillovers, brand effects, and selection bias are not identified.
3. **Time dependence:** Welch tests treat daily observations as independent; seasonality and autocorrelation can make uncertainty appear smaller than it is.
4. **Sparse conversions:** CPA is undefined on zero-conversion days, so CPA tests use valid days only. Fisher tests retain the full click/conversion counts.
5. **Scale response:** Historical efficiency may deteriorate when budget increases. The 30% cap is therefore a risk control, not a claim about the channel's saturation curve.
6. **Statistical vs practical significance:** Adjusted p-values establish evidence against equal performance, but budget decisions also depend on effect size, confidence intervals, capacity, creative quality, and incremental profit.

## Next steps

1. Run a four-week randomized holdout for {top['channel']} and the two largest non-{top['channel']} allocations.
2. Track incremental contribution margin, not platform-reported revenue alone.
3. Re-estimate the model weekly but make budget decisions only at the pre-registered review date.
4. Replace the benchmark with the company's own 90+ days of campaign-level data before moving beyond the proposed caps.
"""
    (PROJECT_ROOT / "executive_memo.md").write_text(memo, encoding="utf-8")


def main() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run Part 5 and generate the decision outputs."""

    ensure_output_directories()
    data = pd.read_csv(MARKETING_DATA, parse_dates=["date"])
    summary = pd.read_csv(TABLES_DIR / "channel_summary.csv")
    cpa = pd.read_csv(TABLES_DIR / "cpa_pairwise_results.csv")
    conversion = pd.read_csv(TABLES_DIR / "fisher_conversion_results.csv")
    sample_sizes = pd.read_csv(TABLES_DIR / "sample_size_recommendations.csv")

    intervals = cpa_confidence_intervals(data)
    allocation = create_budget_allocation(summary)
    findings = significant_findings(cpa, conversion)

    intervals.to_csv(TABLES_DIR / "cpa_confidence_intervals.csv", index=False)
    allocation.to_csv(TABLES_DIR / "budget_allocation.csv", index=False)
    findings.to_csv(TABLES_DIR / "significant_findings.csv", index=False)
    write_executive_memo(summary, cpa, conversion, intervals, allocation, sample_sizes)

    print("\nRecommended monthly budget allocation:")
    print(allocation[["channel", "recommended_share", "recommended_budget_usd", "allocation_guardrail"]].to_string(index=False))
    return intervals, allocation, findings


if __name__ == "__main__":
    main()
