from __future__ import annotations

import unittest

from armour_labs.dataset import load_jsonl
from armour_labs.replay import replay_records


class ReplayTests(unittest.TestCase):
    def test_reviewer_calibrated_policy_improves_live_fixture_metrics(self) -> None:
        records = load_jsonl("datasets/live_external_agent_runs.jsonl")
        baseline = replay_records(records, "baseline")
        calibrated = replay_records(records, "reviewer-calibrated")
        self.assertEqual(baseline["overall"]["accuracy"], 0.5)
        self.assertEqual(calibrated["overall"]["accuracy"], 1.0)
        self.assertEqual(calibrated["overall"]["false_positive"], 0)
        self.assertEqual(calibrated["overall"]["false_negative"], 0)

    def test_replay_records_reports_changes_from_baseline(self) -> None:
        records = load_jsonl("datasets/live_external_agent_runs.jsonl")
        calibrated = replay_records(records, "reviewer-calibrated")
        self.assertGreater(len(calibrated["changes_from_baseline"]), 0)
        self.assertIn("policy_rules", calibrated["changes_from_baseline"][0])


if __name__ == "__main__":
    unittest.main()
