# Integrations

Armour can scan Armour-native traces and MCP-style agent logs.

## MCP JSONL

MCP-style logs are newline-delimited JSON events with tool call and tool result
records. Armour accepts common field names such as:

- `tool`, `tool_name`, or nested `tool_call.name`
- `arguments`, `args`, `parameters`, or nested `tool_call.arguments`
- `result`, `output`, `content`, `response`, or `observation`
- `id`, `call_id`, or `tool_call_id`

Example:

```json
{"type":"tool_call","id":"call_1","tool":"ticket_search","arguments":{"query":"ticket TCK-1042"}}
{"type":"tool_result","tool_call_id":"call_1","result":"Ticket found."}
```

Convert to Armour trace JSON:

```bash
python3 -m armour_labs.cli convert-log examples/agent_logs/mcp_customer_ticket.jsonl --format mcp-jsonl --eval-id customer-ticket-privacy --agent-id example-mcp-agent --out reports/mcp_trace.json
```

Scan directly:

```bash
python3 -m armour_labs.cli scan-log examples/agent_logs/mcp_customer_ticket.jsonl --format mcp-jsonl --eval-id customer-ticket-privacy --agent-id example-mcp-agent
```

## Coding-Agent JSONL

`claude-code-jsonl` currently uses the same permissive event parser as
`mcp-jsonl`. The adapter is intentionally tolerant because local agent logs vary
by harness. The next step is to add exact parsers for specific exported
coding-agent and browser-agent trace formats once those logs are collected.
