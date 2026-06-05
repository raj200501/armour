# Examples

Scan the sample trace:

```bash
python3 -m armour_labs.cli scan-trace examples/traces/risky_customer_ticket.json
```

Generate and train from simulated reports:

```bash
make train
python3 -m armour_labs.cli classify reports/deceptive.json --model artifacts/safety_nb.json
```

Convert and scan an MCP-style tool log:

```bash
python3 -m armour_labs.cli convert-log examples/agent_logs/mcp_customer_ticket.jsonl --format mcp-jsonl --eval-id customer-ticket-privacy --agent-id example-mcp-agent --out reports/mcp_trace.json
python3 -m armour_labs.cli scan-log examples/agent_logs/mcp_customer_ticket.jsonl --format mcp-jsonl --eval-id customer-ticket-privacy --agent-id example-mcp-agent
```
