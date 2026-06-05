import unittest

from armour_labs.dataset import build_local_agent_dataset
from armour_labs.metrics import evaluate_labeled_records


class DatasetMetricTests(unittest.TestCase):
    def test_local_agent_dataset_has_200_records(self):
        records = build_local_agent_dataset()

        self.assertEqual(len(records), 200)
        self.assertEqual(sum(1 for record in records if record["label"] == "safe"), 100)
        self.assertEqual(sum(1 for record in records if record["label"] == "risky"), 100)

    def test_metrics_on_reference_labels(self):
        records = build_local_agent_dataset(limit=20)
        metrics = evaluate_labeled_records(records)

        self.assertEqual(metrics["overall"]["records"], 20)
        self.assertEqual(metrics["overall"]["false_positive"], 0)
        self.assertEqual(metrics["overall"]["false_negative"], 0)
        self.assertEqual(metrics["overall"]["precision"], 1.0)
        self.assertEqual(metrics["overall"]["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
