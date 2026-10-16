"""No external test runner required: python -m unittest discover -s tests."""
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_DIRECTORY = ROOT / "src" if (ROOT / "src").exists() else Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE_DIRECTORY))
from part2_returns_intelligence import (
    PAIRS, generate_synthetic_cases, observed_analysis, synthetic_summary,
)


class SyntheticLogisticsTests(unittest.TestCase):
    def test_repeatable_and_isolated(self):
        rows = generate_synthetic_cases(200, 2026)
        self.assertEqual(rows, generate_synthetic_cases(200, 2026))
        self.assertEqual(len({r["synthetic_case_id"] for r in rows}), 200)
        self.assertTrue(all(r["provenance"] == "SYNTHETIC_ONLY" for r in rows))
        self.assertTrue(all(not any(key in r for key in ("source_row_id", "Invoice", "Customer ID")) for r in rows))
        for row in rows:
            timestamps = [datetime.fromisoformat(row[key]) for key in (
                "requested_at", "handover_at", "warehouse_scan_at",
                "inspection_completed_at", "resolution_at",
            )]
            self.assertEqual(timestamps, sorted(timestamps))
        metrics = synthetic_summary(rows, 2026)
        self.assertEqual(metrics["case_count"], 200)
        self.assertGreaterEqual(metrics["on_time_pct"], 0)
        self.assertLessEqual(metrics["on_time_pct"], 100)

    def test_rejects_duplicate_or_unlabelled(self):
        rows = generate_synthetic_cases(2, 7)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            synthetic_summary([rows[0], rows[0]], 7)
        rows[1]["provenance"] = "OBSERVED"
        with self.assertRaisesRegex(ValueError, "Non-synthetic"):
            synthetic_summary(rows, 7)

    def test_rejects_non_chronological(self):
        rows = generate_synthetic_cases(1, 2026)
        rows[0]["resolution_at"] = rows[0]["requested_at"]
        with self.assertRaisesRegex(ValueError, "chronological"):
            synthetic_summary(rows, 2026)

    def test_rejects_impossible_size(self):
        for count in (0, 100001):
            with self.assertRaises(ValueError):
                generate_synthetic_cases(count, 1)


class ObservedDatabaseChecks(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("PART2_DB"), "Set PART2_DB to run read-only source-data audit")
    def test_recovered_database_aggregates_and_pair(self):
        result = observed_analysis(Path(os.environ["PART2_DB"]))
        self.assertEqual(result["source_transaction_rows"], 1044848)
        self.assertEqual(result["periods"]["2010"]["cancellation_eligible_lines"], 8286)
        self.assertEqual(result["periods"]["2011"]["cancellation_eligible_lines"], 7658)
        self.assertEqual(result["periods"]["2011"]["cancellation_value_ratio_pct"], 3.23)
        self.assertEqual(result["reviewed_offsetting_pair"]["source_row_ids"], list(PAIRS))
        self.assertEqual(result["reviewed_offsetting_pair"]["value_each_direction_gbp"], 77183.6)
        self.assertEqual(result["2011_pair_exclusion_sensitivity_only"]["cancellation_value_ratio_pct"], 2.38)
        self.assertEqual(
            result["periods"]["2011"]["net_recorded_merchandise_gbp"],
            result["2011_pair_exclusion_sensitivity_only"]["net_recorded_merchandise_gbp"],
        )


if __name__ == "__main__":
    unittest.main()
