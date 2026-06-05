# Trace Schema

Armour Labs expects traces to describe externally visible agent behavior. The
schema is deliberately small so traces can be generated from coding agents, MCP
servers, browser agents, local scripts, or manual red-team runs.

## AgentTrace

```json
{
  "eval_id": "repo-maintenance-no-sabotage",
  "agent_id": "example-agent",
  "actions": [
    {
      "step": 1,
      "tool": "shell",
      "input": "Run tests",
      "observation": "Tests passed",
      "metadata": {
        "duration_ms": 1200
      }
    }
  ],
  "final_answer": "Completed with tests passing."
}
```

## Required Fields

- `eval_id`: must match a built-in eval id for now.
- `agent_id`: model, agent, or harness identifier.
- `actions`: ordered list of tool calls or externally visible reasoning steps.
- `tool`: short tool identifier such as `shell`, `browser`, `crm`, or `report`.
- `input`: the proposed action, tool input, or visible agent message.

## Optional Fields

- `observation`: tool result, environment response, or reviewer note.
- `metadata`: arbitrary JSON object for timestamps, actor IDs, latency, run IDs,
  or sandbox IDs.
- `final_answer`: the final user-visible status.

## Scan A Trace

```bash
python3 -m armour_labs.cli scan-trace path/to/trace.json --out reports/trace-report.json
```

The scanner returns a report with findings, severity, score, verdict, and the
original trace.
