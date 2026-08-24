# In Data We Trust: Statistical Marketing Analysis

This repository is Elza Paegle's submission for the Ironhack statistical-analysis lab. It turns a public seven-channel SaaS marketing benchmark into an auditable decision workflow: data validation, descriptive metrics, pairwise hypothesis tests, multiple-comparison corrections, power analysis, and a guarded $500,000 monthly budget recommendation.

## Decision in one minute

- **Referral** leads the benchmark with 6.61x aggregate ROAS, $78 aggregate CPA, and a 2.73% weighted conversion rate.
- Of 21 channel pairs, 16 CPA differences and 15 conversion-rate differences remain significant after Benjamini-Hochberg FDR control.
- Ninety days per channel are sufficient in the simulation for CPA effects of 10% or more, but not for a subtle 5% effect.
- The proposed allocation gives Referral 21.3% ($106,400), retains an 8.0%–18.9% range for the other channels, and applies 5%/30% floor and cap guardrails.
- The source is synthetic. The allocation is therefore a testable starting point, not evidence of causal lift in a real company.

Read [executive_memo.md](executive_memo.md) for the recommendation and [dataset_documentation.md](dataset_documentation.md) for provenance and limitations.

## Repository map

| Path | Purpose |
| --- | --- |
| `run_analysis.py` | Runs the complete workflow in the required order. |
| `src/data_exploration.py` | Validates and aggregates the source; calculates CTR, conversion rate, CPA, ROAS, profit, and margin. |
| `src/statistical_analysis.py` | Runs 21 Welch CPA t-tests and 21 two-sided Fisher exact conversion tests; adds Cohen's d, Bonferroni, and BH-FDR results. |
| `src/power_analysis.py` | Simulates empirical power across 5%–20% CPA effects and 30–180 days; estimates minimum sample sizes. |
| `src/business_recommendations.py` | Bootstraps CPA intervals, builds the constrained budget allocation, and generates the memo. |
| `data/raw/` | Unmodified Hugging Face CSV exports. |
| `data/processed/marketing_data.csv` | 630 daily channel observations used in the tests. |
| `results/tables/` | Machine-readable metrics, test results, corrections, power, confidence intervals, and allocation. |
| `results/figures/` | Six publication-ready statistical and decision charts. |
| `analysis_workbook.xlsx` | Reviewer-friendly workbook containing the main data, tables, formulas, and a native chart. |
| `tests/test_analysis.py` | Regression tests for source quality, metric reconciliation, pair counts, p-values, and budget constraints. |

## Reproduce the analysis

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
```

Activate the environment with `.venv\Scripts\activate` on Windows or `source .venv/bin/activate` on macOS/Linux, then run:

```bash
pip install -r requirements.txt
python run_analysis.py
python -m unittest discover -s tests -v
```

No API key or network connection is required after cloning because the cited raw data is included for reproducibility. Generated tables, figures, the workbook, and the memo are committed so a reviewer can inspect the result without rerunning the code.

## Statistical design

The six synthetic companies are first aggregated to one row per date and channel. This produces 90 observations per channel and avoids treating six measurements from the same channel-day as independent campaign replications.

- **CPA:** two-sided Welch independent t-tests on valid daily CPA observations. Zero-conversion days have undefined CPA and are excluded from this test only. Cohen's d reports practical magnitude.
- **Conversion:** two-sided Fisher exact tests on total conversions versus non-conversions among clicks; all observations are retained.
- **Multiplicity:** results include raw decisions, Bonferroni-adjusted decisions, and Benjamini-Hochberg FDR-adjusted decisions. FDR is the primary prioritization rule; Bonferroni is the conservative sensitivity check.
- **Power:** seeded Monte Carlo simulations use an $800 baseline CPA, 15% standard deviation, two-sided alpha of 0.05, and a target power of 80%.
- **Recommendation:** channels receive rank-based points weighted 50% ROAS, 30% conversion rate, and 20% CPA. Monthly shares are constrained to 5%–30% and rounded to $100 while reconciling exactly to $500,000.

## Interpretation guardrails

Platform-attributed revenue is not incremental revenue. The data is synthetic, daily observations may be autocorrelated, and channel efficiency may deteriorate at higher spend. A live randomized holdout and contribution-margin measurement should precede any larger reallocation. See [reflection.md](reflection.md) for a fuller discussion.

## Data source and license

The analysis uses the public [Solstice SaaS Growth Pack (Sample)](https://huggingface.co/datasets/solsticestudioai/saas-growth-pack), licensed under CC BY 4.0. See [ATTRIBUTION.md](ATTRIBUTION.md) for attribution and [dataset_documentation.md](dataset_documentation.md) for the exact source files and transformations.
