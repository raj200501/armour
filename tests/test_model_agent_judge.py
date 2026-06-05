from __future__ import annotations

import unittest
from typing import Any

from armour_labs.model_agent import collect_model_agent_record, dry_run_plan
from armour_labs.model_judge import dry_run_plan as judge_dry_run_plan
from armour_labs.model_judge import judge_record_with_model


class FakeJsonClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self.payload


class ModelAgentJudgeTests(unittest.TestCase):
    def test_collect_model_agent_record_normalizes_events(self) -> None:
        client = FakeJsonClient(
            {
                "summary": "cautious path",
                "events": [
                    {
                        "tool": "ticket.lookup",
                        "arguments": {"ticket_id": "T-1"},
                        "result": {"status": "ok"},
                    }
                ],
            }
        )
        record = collect_model_agent_record("customer-ticket-privacy", "cautious", client)
        self.assertEqual(record["label"], "safe")
        self.assertEqual(record["agent_family"], "model-backed-agent")
        self.assertEqual(record["events"][0]["type"], "tool_call")
        self.assertEqual(record["events"][0]["id"], "call_1")
        self.assertIn("customer-ticket-privacy", client.user_prompt)

    def test_collect_model_agent_record_rejects_empty_events(self) -> None:
        client = FakeJsonClient({"summary": "bad", "events": []})
        with self.assertRaises(ValueError):
            collect_model_agent_record("customer-ticket-privacy", "cautious", client)

    def test_agent_dry_run_plan_records_secret_policy(self) -> None:
        plan = dry_run_plan(["customer-ticket-privacy"], ["cautious"], "gemini", "gemini-test")
        self.assertEqual(plan["status"], "dry_run")
        self.assertEqual(plan["provider"], "gemini")
        self.assertEqual(plan["records_planned"], 1)
        self.assertIn("not serialized", plan["secret_policy"])

    def test_agent_dry_run_plan_lists_anthropic_env(self) -> None:
        plan = dry_run_plan(["customer-ticket-privacy"], ["cautious"], "anthropic", None)
        self.assertEqual(plan["model"], "ANTHROPIC_MODEL")
        self.assertIn("ANTHROPIC_API_KEY", plan["required_env"]["anthropic"])

    def test_model_judge_coerces_label_strings(self) -> None:
        record = {"id": "trace-1", "label": "safe", "events": [], "eval_id": "customer-ticket-privacy"}
        client = FakeJsonClient({"risk_label": "risky", "confidence": "high", "rationale": "Forbidden tool use."})
        judgment = judge_record_with_model(record, client)
        self.assertTrue(judgment["predicted_risky"])
        self.assertEqual(judgment["confidence"], "high")

    def test_model_judge_dry_run_plan_lists_anthropic_env(self) -> None:
        plan = judge_dry_run_plan("dataset.jsonl", "anthropic", None)
        self.assertEqual(plan["model"], "ANTHROPIC_MODEL")
        self.assertIn("ANTHROPIC_API_KEY", plan["required_env"]["anthropic"])


if __name__ == "__main__":
    unittest.main()
