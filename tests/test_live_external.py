import unittest
from pathlib import Path

from armour_labs.adjudication import build_adjudication_queue
from armour_labs.judge_baseline import evaluate_judge
from armour_labs.live_external import collect_live_external_records
from armour_labs.metrics import evaluate_labeled_records


class LiveExternalTests(unittest.TestCase):
    def test_collects_live_external_records(self):
        records = collect_live_external_records(Path("examples/external_agents/tiny_mcp_agent.py"))

        self.assertEqual(len(records), 32)
        self.assertEqual(sum(1 for record in records if record["label"] == "safe"), 16)
        self.assertEqual(sum(1 for record in records if record["label"] == "risky"), 16)
        self.assertTrue(all(record["events"] for record in records))

    def test_monitor_and_judge_have_expected_metrics_shape(self):
        records = collect_live_external_records(Path("examples/external_agents/tiny_mcp_agent.py"))
        monitor = evaluate_labeled_records(records)
        judge = evaluate_judge(records)
        queue = build_adjudication_queue(records)

        self.assertEqual(monitor["overall"]["records"], 32)
        self.assertEqual(judge["overall"]["records"], 32)
        self.assertGreaterEqual(len(queue), 1)
        self.assertGreaterEqual(monitor["overall"]["false_positive"], 1)
        self.assertGreaterEqual(monitor["overall"]["false_negative"], 1)


if __name__ == "__main__":
    unittest.main()
