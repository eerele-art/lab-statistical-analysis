"""Shared paths, constants, and plotting helpers for the lab."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLES_DIR = PROJECT_ROOT / "results" / "tables"
FIGURES_DIR = PROJECT_ROOT / "results" / "figures"

RAW_CHANNEL_DATA = RAW_DIR / "channel_performance.csv"
RAW_COMPANY_DATA = RAW_DIR / "companies.csv"
MARKETING_DATA = PROCESSED_DIR / "marketing_data.csv"

MONTHLY_BUDGET_USD = 500_000
RANDOM_SEED = 42
ALPHA = 0.05


def ensure_output_directories() -> None:
    """Create deterministic output folders used by every analysis stage."""

    for path in (PROCESSED_DIR, TABLES_DIR, FIGURES_DIR):
        path.mkdir(parents=True, exist_ok=True)


def apply_plot_style() -> None:
    """Apply a restrained, readable style consistently across figures."""

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 180,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "axes.titleweight": "semibold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
        }
    )

