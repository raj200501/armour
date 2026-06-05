import unittest
from pathlib import Path

from armour_labs.adapters import trace_from_agent_log
from armour_labs.runner import scan_trace


class AdapterTests(unittest.TestCase):
    def test_mcp_jsonl_imports_and_scans(self):
        trace = trace_from_agent_log(
            Path("examples/agent_logs/mcp_customer_ticket.jsonl"),
            "mcp-jsonl",
            "customer-ticket-privacy",
            "example-mcp-agent",
        )

        self.assertEqual(trace.eval_id, "customer-ticket-privacy")
        self.assertEqual(trace.agent_id, "example-mcp-agent")
        self.assertEqual(len(trace.actions), 2)
        self.assertEqual(trace.actions[1].tool, "bulk_export")

        report = scan_trace(trace)

        self.assertEqual(report["summary"]["fail_count"], 1)
        self.assertGreater(report["summary"]["critical_findings"], 0)


if __name__ == "__main__":
    unittest.main()
