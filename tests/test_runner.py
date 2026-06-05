import unittest

from armour_labs.runner import run_suite


class RunnerTests(unittest.TestCase):
    def test_benign_profile_passes_suite(self):
        report = run_suite("benign")

        self.assertEqual(report["summary"]["eval_count"], 100)
        self.assertEqual(report["summary"]["fail_count"], 0)
        self.assertEqual(report["summary"]["average_score"], 100)

    def test_sloppy_profile_fails_suite(self):
        report = run_suite("sloppy")

        self.assertEqual(report["summary"]["eval_count"], 100)
        self.assertGreater(report["summary"]["fail_count"], 0)
        self.assertGreater(report["summary"]["critical_findings"], 0)


if __name__ == "__main__":
    unittest.main()
