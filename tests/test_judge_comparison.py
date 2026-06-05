from __future__ import annotations

import unittest

from armour_labs.dataset import load_jsonl
from armour_labs.judge_comparison import build_judge_comparison, claim_target_records
from armour_labs.provenance import load_adjudication


class JudgeComparisonTests(unittest.TestCase):
    def test_claim_target_records_use_external_consensus(self) -> None:
        records = load_jsonl("datasets/model_agent_claim_candidates.jsonl")
        adjudication = load_adjudication("review/reviewer_adjudication.json")

        targets = claim_target_records(records, adjudication)

        self.assertEqual(len(targets), 20)
        self.assertEqual({record["label_source"] for record in targets}, {"anonymous-external-consensus"})

    def test_armour_beats_generic_proxy_on_claim_targets(self) -> None:
        records = load_jsonl("datasets/model_agent_claim_candidates.jsonl")
        adjudication = load_adjudication("review/reviewer_adjudication.json")

        report = build_judge_comparison(records, adjudication)

        armour = report["baselines"]["armour_reviewer_calibrated"]["metrics"]
        generic = report["baselines"]["generic_llm_judge_proxy"]["metrics"]
        self.assertEqual(report["record_count"], 20)
        self.assertEqual(armour["accuracy"], 1.0)
        self.assertEqual(generic["accuracy"], 0.75)
        self.assertEqual(generic["false_negative"], 5)
        self.assertGreater(report["deltas"]["armour_minus_generic_proxy"]["recall"], 0)
        bounds = report["confidence_bounds"]["armour_reviewer_calibrated"]
        self.assertEqual(bounds["accuracy_trials"], 20)
        self.assertEqual(bounds["accuracy_successes"], 20)
        self.assertLess(bounds["accuracy_wilson_95_lower"], 1.0)


if __name__ == "__main__":
    unittest.main()
