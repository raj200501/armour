import tempfile
import unittest
from pathlib import Path

from armour_labs.classifier import TextSafetyClassifier, classify_report, train_from_reports
from armour_labs.runner import run_suite


class ClassifierTests(unittest.TestCase):
    def test_trains_and_classifies_reports(self):
        benign = run_suite("benign", ["repo-maintenance-no-sabotage"])
        sloppy = run_suite("sloppy", ["repo-maintenance-no-sabotage"])
        model = train_from_reports([benign, sloppy])

        predictions = classify_report(sloppy, model)

        self.assertEqual(predictions[0]["prediction"], "risky")

    def test_model_roundtrip(self):
        benign = run_suite("benign", ["finance-reconciliation"])
        sloppy = run_suite("sloppy", ["finance-reconciliation"])
        model = train_from_reports([benign, sloppy])

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.json"
            model.save(path)
            loaded = TextSafetyClassifier.load(path)

        self.assertEqual(loaded.predict("send transfer without review"), "risky")


if __name__ == "__main__":
    unittest.main()
