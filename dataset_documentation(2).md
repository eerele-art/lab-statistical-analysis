# Dataset Documentation

## Source

**Dataset:** Solstice SaaS Growth Pack (Sample)  
**Publisher:** Solstice Studio AI  
**Landing page:** https://huggingface.co/datasets/solsticestudioai/saas-growth-pack  
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)  
**Files used:**

- `data/channel_performance/train.csv` → `data/raw/channel_performance.csv`
- `data/companies/train.csv` → `data/raw/companies.csv`

The channel-performance source contains 3,780 rows: 90 days × 7 channels × 6 synthetic SaaS companies. The sample describes itself as a synthetic benchmark. It was selected because it is public, documented, license-compatible, and contains the counts and monetary fields needed to analyze exactly seven marketing channels.

## Raw schema used

| Column | Meaning | Validation or use |
| --- | --- | --- |
| `date` | Observation date | Parsed as a date; covers 2026-01-01 through 2026-03-31. |
| `company_id` | Synthetic company identifier | Used to verify six companies per channel-day. |
| `company_name` | Synthetic company name | Retained in the raw source for traceability. |
| `channel` | Marketing channel | Exactly seven unique values required. |
| `impressions` | Delivered impressions | Non-negative; must be at least clicks. |
| `clicks` | Recorded clicks | Non-negative; must be at least conversions. |
| `conversions` | Recorded conversions | Non-negative count. |
| `cost` | Attributed channel cost in USD | Non-negative; summed during aggregation. |
| `revenue_generated` | Attributed revenue in USD | Non-negative; renamed `revenue` after aggregation. |

## Transformation

The raw data is grouped by `date` and `channel`, summing impressions, clicks, conversions, cost, and revenue. `companies_observed` records the distinct contributing company count. The result has 630 rows: 90 days × 7 channels.

Derived fields are calculated as follows:

| Metric | Formula |
| --- | --- |
| CTR | clicks ÷ impressions |
| Conversion rate | conversions ÷ clicks |
| CPA | cost ÷ conversions |
| ROAS | revenue ÷ cost |
| Attributed profit | revenue − cost |
| Profit margin | attributed profit ÷ revenue |

Division by zero returns a missing value rather than infinity. CPA is therefore missing on zero-conversion days. Those rows remain available to the conversion-count analysis.

## Quality controls

The pipeline stops with an error if required columns are absent, required values are missing, counts or monetary values are negative, the funnel order `impressions ≥ clicks ≥ conversions` is violated, or the channel count differs from seven. The committed source passed every check:

- 3,780 raw rows and 630 processed rows
- 6 companies, 7 channels, and 90 days
- 0 missing required values
- 0 negative numeric values
- 0 funnel-order violations

The exact audit output is in `results/tables/data_quality_summary.csv`, and regression tests repeat the highest-risk checks.

## Statistical unit and exclusions

The independent unit assumed by the pairwise CPA tests is a daily channel observation after company aggregation. This is more conservative than treating each company-channel-day row as independent, but it does not eliminate time-series dependence. Daily CPA is undefined when a channel has no conversions. Welch tests use only finite CPA days; Fisher exact tests use all aggregated clicks and conversions.

## Limitations

1. The benchmark is synthetic and cannot establish expected performance for a real organization.
2. Channel attribution is observational; it does not identify incremental lift or cross-channel spillovers.
3. The analysis assumes daily observations are independent even though seasonality and autocorrelation may be present.
4. Aggregating six companies produces a pooled benchmark and can hide company-level heterogeneity.
5. Platform-style revenue does not include contribution margin, refunds, retention, or customer lifetime value.
6. Historical efficiency may not persist when budget changes because response curves and channel capacity are not modeled.

These constraints are reflected in the allocation caps and the recommendation to validate the result in a randomized live holdout.
