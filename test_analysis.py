"""Regression checks for the marketing statistical-analysis lab."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from business_recommendations import create_budget_allocation  # noqa: E402
from common import MARKETING_DATA, MONTHLY_BUDGET_USD, TABLES_DIR  # noqa: E402
from data_exploration import load_and_validate_source  # noqa: E402


class AnalysisRegressionTests(unittest.TestCase):
    def test_source_data_quality(self) -> None:
        source = load_and_validate_source()
        self.assertEqual(len(source), 3780)
        self.assertEqual(source["company_id"].nunique(), 6)
        self.assertEqual(source["channel"].nunique(), 7)
        self.assertTrue((source["impressions"] >= source["clicks"]).all())
        self.assertTrue((source["clicks"] >= source["conversions"]).all())

    def test_processed_metric_reconciliation(self) -> None:
        data = pd.read_csv(MARKETING_DATA)
        self.assertEqual(len(data), 630)
        self.assertTrue((data.groupby("channel").size() == 90).all())
        expected_conversion_rate = data["conversions"] / data["clicks"]
        self.assertTrue(np.allclose(data["conversion_rate"], expected_conversion_rate, equal_nan=True))
        expected_profit = data["revenue"] - data["cost"]
        self.assertTrue(np.allclose(data["profit"], expected_profit))

    def test_pairwise_result_counts_and_ranges(self) -> None:
        cpa = pd.read_csv(TABLES_DIR / "cpa_pairwise_results.csv")
        fisher = pd.read_csv(TABLES_DIR / "fisher_conversion_results.csv")
        self.assertEqual(len(cpa), 21)
        self.assertEqual(len(fisher), 21)
        for frame in (cpa, fisher):
            self.assertTrue(frame["p_value"].between(0, 1).all())
            self.assertTrue(frame["p_value_fdr"].between(0, 1).all())
            self.assertTrue(frame["p_value_bonferroni"].between(0, 1).all())

    def test_budget_allocation_is_bounded_and_reconciles(self) -> None:
        summary = pd.read_csv(TABLES_DIR / "channel_summary.csv")
        allocation = create_budget_allocation(summary)
        self.assertAlmostEqual(allocation["recommended_share"].sum(), 1.0, places=9)
        self.assertAlmostEqual(allocation["recommended_budget_usd"].sum(), MONTHLY_BUDGET_USD, places=2)
        self.assertTrue(allocation["recommended_share"].between(0.05, 0.30).all())


if __name__ == "__main__":
    unittest.main()
