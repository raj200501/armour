from __future__ import annotations

import unittest

from armour_labs.external_gate import build_external_gate_status, render_external_gate_status_markdown


class ExternalGateTests(unittest.TestCase):
    def test_status_reports_model_and_review_gaps(self) -> None:
        manifest = {
            "evidence": {
                "model_backed_records": 3,
                "claim_eligible_external_reviewed_records": 4,
                "model_providers": {"gemini": 3},
                "model_names": {"gemini-test": 3},
                "claim_eligible_record_ids": ["trace-1"],
            },
            "claim_status": {
                "ready_for_external_claim": False,
                "gates": {"model_backed_trace_count": False},
                "blocked_reasons": ["Only 3 model-backed records found; need 20."],
                "required_model_backed_records": 20,
                "required_external_reviewed_records": 20,
            },
        }

        status = build_external_gate_status(manifest)

        self.assertFalse(status["ready_for_external_claim"])
        self.assertEqual(status["counts"]["model_backed_gap"], 17)
        self.assertEqual(status["counts"]["external_review_gap"], 16)
        self.assertEqual(status["provider_coverage"]["model_providers"], {"gemini": 3})

    def test_markdown_keeps_claim_discipline_visible(self) -> None:
        status = build_external_gate_status(
            {
                "evidence": {"model_backed_records": 0, "claim_eligible_external_reviewed_records": 0},
                "claim_status": {"ready_for_external_claim": False},
            }
        )

        markdown = render_external_gate_status_markdown(status)

        self.assertIn("Ready for external claim: `False`", markdown)
        self.assertIn("Do not count dry-run", markdown)
        self.assertIn("run_model_agent_benchmark.py", markdown)


if __name__ == "__main__":
    unittest.main()
