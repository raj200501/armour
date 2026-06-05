import unittest

from armour_labs.metrics import evaluate_labeled_records
from armour_labs.reviewed_fixtures import build_reviewed_external_dataset


class ReviewedFixtureTests(unittest.TestCase):
    def test_reviewed_external_dataset_shape(self):
        records = build_reviewed_external_dataset()

        self.assertEqual(len(records), 22)
        self.assertEqual(sum(1 for record in records if record["label"] == "safe"), 11)
        self.assertEqual(sum(1 for record in records if record["label"] == "risky"), 11)
        self.assertTrue(all(len(record["reviews"]) == 2 for record in records))

    def test_reviewed_external_metrics_include_known_hard_cases(self):
        metrics = evaluate_labeled_records(build_reviewed_external_dataset())
        overall = metrics["overall"]

        self.assertEqual(overall["records"], 22)
        self.assertEqual(overall["true_positive"], 10)
        self.assertEqual(overall["true_negative"], 10)
        self.assertEqual(overall["false_positive"], 1)
        self.assertEqual(overall["false_negative"], 1)
        self.assertEqual(len(metrics["errors"]), 2)


if __name__ == "__main__":
    unittest.main()
