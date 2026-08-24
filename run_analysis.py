"""Run the complete lab pipeline from the repository root."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from business_recommendations import main as recommendations_main  # noqa: E402
from data_exploration import main as exploration_main  # noqa: E402
from power_analysis import main as power_main  # noqa: E402
from statistical_analysis import main as statistics_main  # noqa: E402


def main() -> None:
    exploration_main()
    statistics_main()
    power_main()
    recommendations_main()
    print("\nAnalysis complete. See data/processed, results/tables, results/figures, and executive_memo.md.")


if __name__ == "__main__":
    main()

