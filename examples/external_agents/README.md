# External Agent Harness

`tiny_mcp_agent.py` is a deterministic offline agent fixture that emits
MCP-style JSONL events. It lives outside the `armour_labs` package so Benchmark
v3 can collect traces by executing a separate harness.

Run one trace:

```bash
python3 examples/external_agents/tiny_mcp_agent.py --eval-id customer-ticket-privacy --mode obvious_risk
```

Generate the live external-harness dataset:

```bash
python3 scripts/run_live_external_agent_benchmark.py
```

Modes:

- `cautious`: safe trace
- `obvious_risk`: risky trace with direct forbidden/red-flag action
- `credential_negation`: safe trace that mentions secrets only as prohibited
- `subtle_overreach`: risky trace that over-accesses context without obvious
  keyword triggers

This is not a model-backed agent. Its purpose is to validate the trace
collection, monitor, judge-baseline, and adjudication workflow before spending
money on live model calls.
