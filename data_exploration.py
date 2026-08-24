"""Clean the source data, calculate marketing metrics, and create overview charts."""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from common import (
    FIGURES_DIR,
    MARKETING_DATA,
    RAW_CHANNEL_DATA,
    TABLES_DIR,
    apply_plot_style,
    ensure_output_directories,
)


REQUIRED_COLUMNS = {
    "date",
    "company_id",
    "company_name",
    "channel",
    "impressions",
    "clicks",
    "conversions",
    "cost",
    "revenue_generated",
}


def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divide while returning NaN for zero denominators and non-finite results."""

    result = numerator.div(denominator.replace(0, np.nan))
    return result.replace([np.inf, -np.inf], np.nan)


def load_and_validate_source(path=RAW_CHANNEL_DATA) -> pd.DataFrame:
    """Load the Hugging Face source and enforce the documented data invariants."""

    source = pd.read_csv(path, parse_dates=["date"])
    missing_columns = REQUIRED_COLUMNS.difference(source.columns)
    if missing_columns:
        raise ValueError(f"Source data is missing columns: {sorted(missing_columns)}")

    numeric_columns = [
        "impressions",
        "clicks",
        "conversions",
        "cost",
        "revenue_generated",
    ]
    source[numeric_columns] = source[numeric_columns].apply(pd.to_numeric, errors="raise")

    if source[list(REQUIRED_COLUMNS)].isna().any().any():
        raise ValueError("Required source fields contain missing values.")
    if (source[numeric_columns] < 0).any().any():
        raise ValueError("Counts, cost, and revenue must be non-negative.")
    if not ((source["impressions"] >= source["clicks"]) & (source["clicks"] >= source["conversions"])).all():
        raise ValueError("Expected impressions >= clicks >= conversions for every row.")
    if source["channel"].nunique() != 7:
        raise ValueError("This analysis expects exactly seven marketing channels.")

    return source.sort_values(["date", "channel", "company_id"]).reset_index(drop=True)


def prepare_daily_channel_data(source: pd.DataFrame) -> pd.DataFrame:
    """Aggregate six synthetic companies into one 90-day, seven-channel benchmark."""

    daily = (
        source.groupby(["date", "channel"], as_index=False)
        .agg(
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
            conversions=("conversions", "sum"),
            cost=("cost", "sum"),
            revenue=("revenue_generated", "sum"),
            companies_observed=("company_id", "nunique"),
        )
        .sort_values(["date", "channel"])
        .reset_index(drop=True)
    )

    daily["ctr"] = safe_ratio(daily["clicks"], daily["impressions"])
    daily["conversion_rate"] = safe_ratio(daily["conversions"], daily["clicks"])
    daily["cpa"] = safe_ratio(daily["cost"], daily["conversions"])
    daily["roas"] = safe_ratio(daily["revenue"], daily["cost"])
    daily["profit"] = daily["revenue"] - daily["cost"]
    daily["profit_margin"] = safe_ratio(daily["profit"], daily["revenue"])

    return daily


def calculate_channel_summary(daily: pd.DataFrame) -> pd.DataFrame:
    """Calculate totals, weighted rates, and daily distribution statistics."""

    summary = (
        daily.groupby("channel", as_index=False)
        .agg(
            days=("date", "nunique"),
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
            conversions=("conversions", "sum"),
            cost=("cost", "sum"),
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
            valid_cpa_days=("cpa", "count"),
            daily_cpa_mean=("cpa", "mean"),
            daily_cpa_std=("cpa", "std"),
            daily_roas_mean=("roas", "mean"),
            daily_conversion_rate_mean=("conversion_rate", "mean"),
        )
    )
    summary["ctr"] = safe_ratio(summary["clicks"], summary["impressions"])
    summary["conversion_rate"] = safe_ratio(summary["conversions"], summary["clicks"])
    summary["cpa"] = safe_ratio(summary["cost"], summary["conversions"])
    summary["roas"] = safe_ratio(summary["revenue"], summary["cost"])
    summary["profit_margin"] = safe_ratio(summary["profit"], summary["revenue"])
    return summary.sort_values("roas", ascending=False).reset_index(drop=True)


def save_quality_summary(source: pd.DataFrame, daily: pd.DataFrame) -> None:
    """Write auditable quality checks used to support the exploration narrative."""

    quality = pd.DataFrame(
        [
            ("source_rows", len(source)),
            ("processed_rows", len(daily)),
            ("source_companies", source["company_id"].nunique()),
            ("channels", daily["channel"].nunique()),
            ("days", daily["date"].nunique()),
            ("required_missing_values", int(source[list(REQUIRED_COLUMNS)].isna().sum().sum())),
            ("negative_numeric_values", int((source[["impressions", "clicks", "conversions", "cost", "revenue_generated"]] < 0).sum().sum())),
            ("funnel_invariant_violations", int((~((source["impressions"] >= source["clicks"]) & (source["clicks"] >= source["conversions"]))).sum())),
        ],
        columns=["check", "value"],
    )
    quality.to_csv(TABLES_DIR / "data_quality_summary.csv", index=False)


def plot_group_metrics(summary: pd.DataFrame) -> None:
    """Create a six-panel executive overview of channel performance."""

    apply_plot_style()
    ordered = summary.sort_values("roas", ascending=True).copy()
    colors = ["#0F766E" if channel == "Referral" else "#94A3B8" for channel in ordered["channel"]]

    panels = [
        ("cpa", "CPA (USD, lower is better)", "${:,.0f}"),
        ("roas", "ROAS (revenue / cost)", "{:.2f}x"),
        ("conversion_rate", "Conversion rate", "{:.2%}"),
        ("conversions", "Total conversions", "{:,.0f}"),
        ("cost", "Total cost (USD)", "${:,.0f}"),
        ("profit", "Attributed profit (USD)", "${:,.0f}"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(17, 10), constrained_layout=True)
    for ax, (column, title, value_format) in zip(axes.flat, panels):
        bars = ax.barh(ordered["channel"], ordered[column], color=colors)
        ax.set_title(title)
        ax.set_xlabel("")
        ax.grid(axis="x", alpha=0.25)
        ax.grid(axis="y", visible=False)
        if column == "profit":
            ax.axvline(0, color="#334155", linewidth=0.8)
        for bar, value in zip(bars, ordered[column]):
            x = bar.get_width()
            if column == "profit" and value < 0:
                ax.text(
                    x / 2,
                    bar.get_y() + bar.get_height() / 2,
                    value_format.format(value),
                    va="center",
                    ha="center",
                    fontsize=8,
                    color="#0F172A",
                )
                continue
            alignment = "left" if x >= 0 else "right"
            offset = max(abs(ordered[column]).max() * 0.012, 0.01)
            label_x = x + offset if x >= 0 else x - offset
            ax.text(label_x, bar.get_y() + bar.get_height() / 2, value_format.format(value), va="center", ha=alignment, fontsize=8)

    fig.suptitle("Seven-channel marketing performance — 90-day benchmark", fontsize=16, fontweight="bold")
    fig.savefig(FIGURES_DIR / "group_metrics_overview.png", bbox_inches="tight")
    plt.close(fig)


def plot_distributions(daily: pd.DataFrame) -> None:
    """Show daily variability for CPA, conversion rate, and ROAS."""

    apply_plot_style()
    order = daily.groupby("channel")["roas"].mean().sort_values(ascending=False).index.tolist()
    fig, axes = plt.subplots(1, 3, figsize=(19, 6), constrained_layout=True)
    metrics = [
        ("cpa", "Daily CPA distribution", "CPA (USD)"),
        ("conversion_rate", "Daily conversion-rate distribution", "Conversion rate"),
        ("roas", "Daily ROAS distribution", "ROAS"),
    ]
    for ax, (metric, title, ylabel) in zip(axes, metrics):
        plot_data = daily.replace([np.inf, -np.inf], np.nan).dropna(subset=[metric])
        sns.boxplot(data=plot_data, x="channel", y=metric, order=order, ax=ax, color="#5EEAD4", fliersize=2)
        ax.set_title(title)
        ax.set_xlabel("")
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=38)
        if metric == "conversion_rate":
            ax.yaxis.set_major_formatter(plt.matplotlib.ticker.PercentFormatter(1.0))
        ax.grid(axis="y", alpha=0.25)
        ax.grid(axis="x", visible=False)

    fig.suptitle("Daily variability matters: point estimates do not tell the whole story", fontsize=15, fontweight="bold")
    fig.savefig(FIGURES_DIR / "group_distributions.png", bbox_inches="tight")
    plt.close(fig)


def main() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run Part 1 and return the processed data and channel summary."""

    ensure_output_directories()
    source = load_and_validate_source()
    daily = prepare_daily_channel_data(source)
    summary = calculate_channel_summary(daily)

    daily.to_csv(MARKETING_DATA, index=False, date_format="%Y-%m-%d")
    summary.to_csv(TABLES_DIR / "channel_summary.csv", index=False)
    save_quality_summary(source, daily)
    plot_group_metrics(summary)
    plot_distributions(daily)

    print(f"Prepared {len(daily):,} daily-channel observations across {daily['channel'].nunique()} channels.")
    print(summary[["channel", "conversion_rate", "cpa", "roas", "profit"]].round(4).to_string(index=False))
    return daily, summary


if __name__ == "__main__":
    main()
