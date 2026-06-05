from __future__ import annotations

import csv
import io
import unittest

from armour_labs.reviewer_packet import blind_review_items, build_review_items, packet_summary, response_template_csv


class ReviewerPacketTests(unittest.TestCase):
    def test_blind_items_hide_reference_labels(self) -> None:
        records = [
            {
                "id": "trace-1",
                "eval_id": "customer-ticket-privacy",
                "agent_id": "agent-1",
                "agent_family": "support-agent",
                "policy": "risky",
                "label": "risky",
                "label_source": "fixture",
                "monitor_expectation": "true_positive",
                "review_notes": "Should not appear in blind packet.",
                "events": [{"type": "tool_call", "tool": "crm", "arguments": {"lookup": "unrelated account"}}],
            }
        ]
        items = build_review_items(records, limit=1)
        blind = blind_review_items(items)
        self.assertEqual(blind[0]["source_record_id"], "trace-1")
        self.assertNotIn("reference_label", blind[0])
        self.assertNotIn("label_source", blind[0])
        self.assertNotIn("review_notes", blind[0])

    def test_adjudication_records_are_prioritized(self) -> None:
        records = [
            {"id": "trace-low", "eval_id": "eval-a", "agent_id": "a", "events": [], "label": "safe"},
            {"id": "trace-high", "eval_id": "eval-b", "agent_id": "b", "events": [], "label": "risky"},
        ]
        adjudication = [{"id": "trace-high", "adjudication_reason": "monitor_label_disagreement"}]
        items = build_review_items(records, adjudication_queue=adjudication, limit=2)
        self.assertEqual(items[0]["source_record_id"], "trace-high")
        self.assertEqual(items[0]["priority"], "high")

    def test_response_template_has_one_row_per_item(self) -> None:
        records = [
            {"id": "trace-1", "eval_id": "eval-a", "agent_id": "a", "events": [], "label": "safe"},
            {"id": "trace-2", "eval_id": "eval-b", "agent_id": "b", "events": [], "label": "risky"},
        ]
        items = build_review_items(records, limit=2)
        rows = list(csv.DictReader(io.StringIO(response_template_csv(items))))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["review_id"], "review-001")

    def test_packet_summary_counts_high_priority_items(self) -> None:
        records = [{"id": "trace-1", "eval_id": "eval-a", "agent_id": "a", "events": [], "label": "safe"}]
        items = build_review_items(records, adjudication_queue=[{"id": "trace-1"}], limit=1)
        summary = packet_summary(items)
        self.assertEqual(summary["review_items"], 1)
        self.assertEqual(summary["high_priority_items"], 1)


if __name__ == "__main__":
    unittest.main()
