from __future__ import annotations

import csv
import io
import unittest

from armour_labs.reviewer_intake import (
    build_reviewer_intake_status,
    combine_response_csvs,
    external_response_template_csv,
    missing_external_assignments_csv,
    render_reviewer_handoff_prompt,
)


class ReviewerIntakeTests(unittest.TestCase):
    def test_status_separates_first_party_from_external_rows(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval-a", "priority": "high"}]
        responses = (
            "assignment_id,review_id,reviewer_id,label,confidence,rationale,relevant_steps,monitor_verdict_correct,notes\n"
            "review-001:r1,review-001,raj_kashikar_2026_06,safe,high,Scoped behavior,1;2,unclear,\n"
            "review-001:r2,review-001,,,,,,,\n"
        )

        status = build_reviewer_intake_status(responses, items)

        self.assertEqual(status["completed_response_rows"], 1)
        self.assertEqual(status["first_party_response_rows"], 1)
        self.assertEqual(status["external_response_rows"], 0)
        self.assertEqual(status["missing_external_response_rows"], 2)
        self.assertFalse(status["claim_ready"])

    def test_missing_external_assignments_create_two_slots(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval-a", "priority": "high"}]

        rows = list(csv.DictReader(io.StringIO(missing_external_assignments_csv(items))))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["assignment_id"], "review-001:external-r1")
        self.assertEqual(rows[0]["status"], "needs_external_reviewer")

    def test_missing_external_assignments_skip_completed_anonymous_slots(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval-a", "priority": "high"}]
        anonymous = (
            "assignment_id,review_id,reviewer_id,label,confidence,rationale,relevant_steps,monitor_verdict_correct,notes\n"
            "review-001:anon-r1,review-001,anon_ai_safety_eval_2026_06,safe,high,Scoped behavior,1,unclear,\n"
            "review-001:anon-r2,review-001,anon_enterprise_security_2026_06,safe,high,Scoped behavior,1,unclear,\n"
        )

        rows = list(csv.DictReader(io.StringIO(missing_external_assignments_csv(items, response_csv_text=anonymous))))

        self.assertEqual(rows, [])

    def test_external_response_template_matches_reviewer_columns(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval-a"}]

        rows = list(csv.DictReader(io.StringIO(external_response_template_csv(items))))

        self.assertEqual(rows[0]["review_id"], "review-001")
        self.assertIn("reviewer_id", rows[0])
        self.assertIn("rationale", rows[0])

    def test_combine_response_csvs_counts_external_rows(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval-a"}]
        first_party = (
            "assignment_id,review_id,reviewer_id,label,confidence,rationale,relevant_steps,monitor_verdict_correct,notes\n"
            "review-001:r1,review-001,raj_kashikar_2026_06,safe,high,Scoped behavior,1,unclear,\n"
        )
        external = (
            "assignment_id,review_id,reviewer_id,label,confidence,rationale,relevant_steps,monitor_verdict_correct,notes\n"
            "review-001:external-r1,review-001,external_a_2026_06,safe,high,Scoped behavior,1,unclear,\n"
        )

        status = build_reviewer_intake_status(combine_response_csvs([first_party, external]), items)

        self.assertEqual(status["first_party_response_rows"], 1)
        self.assertEqual(status["external_response_rows"], 1)
        self.assertEqual(status["missing_external_response_rows"], 1)

    def test_anonymous_external_rows_count_as_external_with_provenance(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval-a"}]
        anonymous = (
            "assignment_id,review_id,reviewer_id,label,confidence,rationale,relevant_steps,monitor_verdict_correct,notes\n"
            "review-001:anon-r1,review-001,anon_ai_safety_eval_2026_06,safe,high,Scoped behavior,1,unclear,\n"
            "review-001:anon-r2,review-001,anon_enterprise_security_2026_06,safe,high,Scoped behavior,1,unclear,\n"
        )

        status = build_reviewer_intake_status(anonymous, items)

        self.assertEqual(status["anonymous_external_response_rows"], 2)
        self.assertEqual(status["external_response_rows"], 2)
        self.assertEqual(status["claim_eligible_external_items"], 1)
        self.assertTrue(status["claim_ready"])

    def test_handoff_prompt_warns_about_ai_reviewers(self) -> None:
        prompt = render_reviewer_handoff_prompt()

        self.assertIn("independent AI safety trace reviewer", prompt)
        self.assertIn("must not be represented as independent external human validation", prompt)


if __name__ == "__main__":
    unittest.main()
