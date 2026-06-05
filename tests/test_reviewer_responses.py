from __future__ import annotations

import unittest

from armour_labs.reviewer_responses import adjudicate_responses, parse_reviewer_csv


class ReviewerResponseTests(unittest.TestCase):
    def test_parse_reviewer_csv_skips_blank_template_rows(self) -> None:
        text = (
            "review_id,reviewer_id,label,confidence,rationale,relevant_steps,monitor_verdict_correct,notes\n"
            "review-001,,,,,,,\n"
            "review-001,reviewer-a,safe,high,Looks safe,\"1,3\",yes,\n"
        )
        rows = parse_reviewer_csv(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["review_id"], "review-001")
        self.assertEqual(rows[0]["relevant_steps"], [1, 3])
        self.assertTrue(rows[0]["monitor_verdict_correct"])

    def test_parse_reviewer_csv_rejects_invalid_label(self) -> None:
        text = (
            "review_id,reviewer_id,label,confidence,rationale,relevant_steps,monitor_verdict_correct,notes\n"
            "review-001,reviewer-a,bad,high,Nope,1,yes,\n"
        )
        with self.assertRaises(ValueError):
            parse_reviewer_csv(text)

    def test_adjudicate_responses_requires_two_reviewers_for_completion(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval", "reference_label": "safe"}]
        responses = [
            {"review_id": "review-001", "reviewer_id": "reviewer-a", "label": "safe"},
        ]
        result = adjudicate_responses(items, responses)
        item = result["items"][0]
        self.assertEqual(item["disposition"], "insufficient_reviewers")
        self.assertEqual(result["summary"]["complete_items"], 0)

    def test_adjudicate_responses_marks_consensus(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval", "reference_label": "risky"}]
        responses = [
            {"review_id": "review-001", "reviewer_id": "reviewer-a", "label": "risky"},
            {"review_id": "review-001", "reviewer_id": "reviewer-b", "label": "risky"},
        ]
        result = adjudicate_responses(items, responses)
        item = result["items"][0]
        self.assertEqual(item["disposition"], "consensus")
        self.assertEqual(item["consensus_label"], "risky")
        self.assertTrue(item["matches_reference"])
        self.assertTrue(item["claim_eligible_external_review"])

    def test_adjudicate_responses_keeps_first_party_out_of_external_claims(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval", "reference_label": "safe"}]
        responses = [
            {"review_id": "review-001", "reviewer_id": "raj_kashikar_2026_06", "label": "safe"},
            {"review_id": "review-001", "reviewer_id": "external-a", "label": "safe"},
        ]

        result = adjudicate_responses(items, responses)
        item = result["items"][0]

        self.assertEqual(item["disposition"], "consensus")
        self.assertEqual(item["first_party_reviewer_count"], 1)
        self.assertEqual(item["external_reviewer_count"], 1)
        self.assertFalse(item["claim_eligible_external_review"])
        self.assertEqual(result["summary"]["claim_eligible_external_items"], 0)

    def test_adjudicate_responses_counts_anonymous_external_reviewers(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval", "reference_label": "safe"}]
        responses = [
            {"review_id": "review-001", "reviewer_id": "anon_ai_safety_eval_2026_06", "label": "safe"},
            {"review_id": "review-001", "reviewer_id": "anon_enterprise_security_2026_06", "label": "safe"},
        ]

        result = adjudicate_responses(items, responses)
        item = result["items"][0]

        self.assertEqual(item["anonymous_external_reviewer_count"], 2)
        self.assertEqual(item["external_reviewer_count"], 2)
        self.assertTrue(item["claim_eligible_external_review"])
        self.assertEqual(result["summary"]["anonymous_external_response_rows"], 2)
        self.assertEqual(result["summary"]["external_response_rows"], 2)


if __name__ == "__main__":
    unittest.main()
