from __future__ import annotations

import unittest

from armour_labs.dataset import load_jsonl
from armour_labs.outcome_state import build_outcome_state_report, classify_action_outcome


class OutcomeStateTests(unittest.TestCase):
    def test_classify_action_outcome_distinguishes_denied_and_succeeded(self) -> None:
        self.assertEqual(
            classify_action_outcome({"tool": "credential_store", "observation": "Access Denied: forbidden tool"}),
            "denied",
        )
        self.assertEqual(
            classify_action_outcome({"tool": "external_upload", "observation": "Payload successfully transmitted"}),
            "succeeded",
        )
        self.assertEqual(classify_action_outcome({"tool": "label_admin", "input": "attempt override"}), "attempted_only")

    def test_outcome_state_report_counts_claim_candidate_outcomes(self) -> None:
        records = load_jsonl("datasets/model_agent_claim_candidates.jsonl")

        report = build_outcome_state_report(records)

        self.assertEqual(report["summary"]["records"], 21)
        self.assertGreater(report["summary"]["records_with_risky_actions"], 0)
        self.assertGreater(report["summary"]["outcome_counts"].get("succeeded", 0), 0)
        self.assertGreater(report["summary"]["outcome_counts"].get("denied", 0), 0)


if __name__ == "__main__":
    unittest.main()
