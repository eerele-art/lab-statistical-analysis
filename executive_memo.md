# Executive Memo: Seven-Channel Marketing Budget Allocation

**Date:** 24 August 2026  
**Analyst:** Elza Paegle  
**Decision:** Allocation of a $500,000 monthly marketing budget  
**Dataset:** Solstice SaaS Growth Pack, channel performance sample  
**Period:** 1 January–31 March 2026 (90 days; seven channels; six synthetic companies aggregated by day)

## Executive summary

The evidence supports a controlled shift toward **Referral**, not an unconstrained reallocation. It delivered the strongest aggregate ROAS (6.61x), lowest aggregate CPA ($78), and highest weighted conversion rate (2.73%); by comparison, the next-best ROAS was only 0.61x and LinkedIn Ads produced the weakest ROAS (0.29x). Pairwise testing confirms that many differences are larger than sampling noise even after multiplicity control. However, the source is a transparent synthetic benchmark rather than observed company data, attribution is not causal, daily observations may be autocorrelated, and cost or demand can change when spend scales. I therefore recommend a **30% cap** on Referral, a **5% learning floor** for every channel, and staged reallocation using the table below. Release the next budget step only after a live four-week geo- or audience-level holdout confirms incremental profit.

## Key findings

- **CPA tests:** 16 of 21 pairs were significant before correction, 15 after Bonferroni, and 16 after Benjamini–Hochberg FDR.
- **Conversion tests:** 16 of 21 pairs were significant before correction, 13 after Bonferroni, and 15 after FDR.
- **Portfolio economics:** Referral generated $257,107 in attributed profit in the benchmark; the other channels should be treated as learning or upper-funnel investments until incrementality is demonstrated.
- **Power:** approximately 40 days per channel are required to detect a 10% CPA difference with 80% power under the simulation assumptions; a 15% effect requires about 20 days. The current 90-day window is sufficient for simulated effects of 10% or more, but not for a subtle 5% difference.
- **Multiplicity choice:** FDR is the main decision rule because the objective is to prioritize promising channels while controlling the expected proportion of false discoveries; Bonferroni is retained as a conservative sensitivity check.

## Recommended monthly allocation

The score weights ROAS at 50%, conversion rate at 30%, and CPA at 20%. Shares are bounded between 5% and 30% to limit model and concentration risk.

| channel | recommended_share | recommended_budget_usd | allocation_guardrail |
| --- | --- | --- | --- |
| Referral | 21.3% | $106,400 | score-weighted |
| SEO | 18.9% | $94,600 | score-weighted |
| Partnerships | 13.6% | $67,900 | score-weighted |
| Paid Search | 13.4% | $66,800 | score-weighted |
| Outbound Sales | 12.4% | $62,100 | score-weighted |
| Content | 12.4% | $62,100 | score-weighted |
| LinkedIn Ads | 8.0% | $40,100 | score-weighted |

## Daily CPA uncertainty

The intervals below are non-parametric 95% percentile bootstrap intervals for mean daily CPA, using only days with at least one conversion.

| channel | mean_daily_cpa | ci_95_lower | ci_95_upper | valid_days |
| --- | --- | --- | --- | --- |
| Referral | $84 | $76 | $94 | 90 |
| Content | $792 | $729 | $854 | 70 |
| SEO | $796 | $732 | $862 | 83 |
| Partnerships | $876 | $809 | $944 | 69 |
| Paid Search | $1,110 | $1,022 | $1,203 | 90 |
| Outbound Sales | $1,171 | $1,084 | $1,262 | 72 |
| LinkedIn Ads | $1,293 | $1,206 | $1,380 | 66 |

## Statistical caveats

1. **Synthetic benchmark:** The Hugging Face source is public and well documented but contains simulated SaaS companies, not this firm's transactions. It is appropriate for demonstrating the workflow, not for claiming realized lift.
2. **Observational attribution:** ROAS and profit are attributed, not incremental. Cross-channel spillovers, brand effects, and selection bias are not identified.
3. **Time dependence:** Welch tests treat daily observations as independent; seasonality and autocorrelation can make uncertainty appear smaller than it is.
4. **Sparse conversions:** CPA is undefined on zero-conversion days, so CPA tests use valid days only. Fisher tests retain the full click/conversion counts.
5. **Scale response:** Historical efficiency may deteriorate when budget increases. The 30% cap is therefore a risk control, not a claim about the channel's saturation curve.
6. **Statistical vs practical significance:** Adjusted p-values establish evidence against equal performance, but budget decisions also depend on effect size, confidence intervals, capacity, creative quality, and incremental profit.

## Next steps

1. Run a four-week randomized holdout for Referral and the two largest non-Referral allocations.
2. Track incremental contribution margin, not platform-reported revenue alone.
3. Re-estimate the model weekly but make budget decisions only at the pre-registered review date.
4. Replace the benchmark with the company's own 90+ days of campaign-level data before moving beyond the proposed caps.
