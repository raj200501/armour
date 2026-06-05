from __future__ import annotations

import csv
import io
import unittest

from armour_labs.reviewer_campaign import (
    assignment_matrix_csv,
    assignment_rows,
    campaign_summary,
    external_reviewer_response_template_csv,
    merge_assignment_matrix_csv,
    merge_recruitment_tracker_csv,
    merge_response_template_csv,
    recruitment_tracker_csv,
    two_reviewer_response_template_csv,
)


class ReviewerCampaignTests(unittest.TestCase):
    def test_assignment_rows_create_two_slots_per_item(self) -> None:
        items = [
            {"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval-a", "priority": "high"},
            {"review_id": "review-002", "source_record_id": "trace-2", "eval_id": "eval-b", "priority": "normal"},
        ]

        rows = assignment_rows(items, reviewers_per_item=2)

        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["assignment_id"], "review-001:r1")
        self.assertEqual(rows[1]["assignment_id"], "review-001:r2")
        self.assertEqual(rows[0]["status"], "planned")

    def test_two_reviewer_template_keeps_response_columns(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval-a"}]

        rows = list(csv.DictReader(io.StringIO(two_reviewer_response_template_csv(items))))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["review_id"], "review-001")
        self.assertIn("reviewer_id", rows[0])
        self.assertIn("label", rows[0])

    def test_merge_response_template_preserves_completed_rows(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval-a"}]
        generated = two_reviewer_response_template_csv(items)
        existing = (
            "assignment_id,review_id,reviewer_id,label,confidence,rationale,relevant_steps,monitor_verdict_correct,notes\n"
            "review-001:r1,review-001,raj_kashikar_2026_06,safe,high,Scoped behavior,1;2,unclear,\n"
            "review-001:r2,review-001,,,,,,,\n"
        )

        rows = list(csv.DictReader(io.StringIO(merge_response_template_csv(generated, existing))))

        self.assertEqual(rows[0]["reviewer_id"], "raj_kashikar_2026_06")
        self.assertEqual(rows[0]["label"], "safe")
        self.assertEqual(rows[1]["reviewer_id"], "")

    def test_merge_assignment_matrix_preserves_reviewer_assignment(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval-a"}]
        generated = assignment_matrix_csv(items)
        existing = (
            "assignment_id,review_id,source_record_id,eval_id,priority,reviewer_slot,assigned_reviewer_id,reviewer_email,status\n"
            "review-001:r1,review-001,trace-1,eval-a,normal,reviewer_1,external_a,a@example.com,sent\n"
            "review-001:r2,review-001,trace-1,eval-a,normal,reviewer_2,,,\n"
        )

        rows = list(csv.DictReader(io.StringIO(merge_assignment_matrix_csv(generated, existing))))

        self.assertEqual(rows[0]["assigned_reviewer_id"], "external_a")
        self.assertEqual(rows[0]["reviewer_email"], "a@example.com")
        self.assertEqual(rows[0]["status"], "sent")

    def test_merge_recruitment_tracker_preserves_contact_state(self) -> None:
        generated = recruitment_tracker_csv(target_count=1)
        existing = (
            "target_id,role,name,email,source,ask,success_signal,status,sent_at,reply_at,next_action\n"
            "reviewer-target-01,ai_safety_researcher,Ada,a@example.com,warm intro,review 5 traces,critique,sent,2026-06-04,,follow up\n"
        )

        rows = list(csv.DictReader(io.StringIO(merge_recruitment_tracker_csv(generated, existing))))

        self.assertEqual(rows[0]["name"], "Ada")
        self.assertEqual(rows[0]["email"], "a@example.com")
        self.assertEqual(rows[0]["status"], "sent")
        self.assertEqual(rows[0]["next_action"], "follow up")

    def test_external_reviewer_template_uses_external_assignment_ids(self) -> None:
        items = [{"review_id": "review-001", "source_record_id": "trace-1", "eval_id": "eval-a"}]

        rows = list(csv.DictReader(io.StringIO(external_reviewer_response_template_csv(items))))

        self.assertEqual(rows[0]["assignment_id"], "review-001:external-r1")
        self.assertEqual(rows[1]["assignment_id"], "review-001:external-r2")

    def test_recruitment_tracker_has_target_rows(self) -> None:
        rows = list(csv.DictReader(io.StringIO(recruitment_tracker_csv(target_count=3))))

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["status"], "not_contacted")
        self.assertIn("review", rows[0]["ask"])

    def test_campaign_summary_counts_required_response_rows(self) -> None:
        items = [{"review_id": "review-001"}, {"review_id": "review-002"}]

        summary = campaign_summary(items, reviewers_per_item=2, target_count=5)

        self.assertEqual(summary["review_items"], 2)
        self.assertEqual(summary["required_response_rows"], 4)
        self.assertEqual(summary["reviewer_targets"], 5)


if __name__ == "__main__":
    unittest.main()
