# Adjudication Workflow

Use adjudication when monitor predictions, judge predictions, or labels
disagree.

## Queue

Benchmark v3 writes:

```bash
datasets/adjudication_queue_v3.jsonl
```

Each record includes:

- record id
- eval id
- reference label
- Armour monitor verdict
- offline judge prediction
- monitor finding rules
- judge rationale
- review notes
- adjudication reason

## Review Steps

1. Read the original dataset record.
2. Inspect the MCP events around the relevant action.
3. Decide whether the reference label, monitor verdict, or judge verdict should
   change.
4. Record reviewer id, label, confidence, rationale, and relevant action steps.
5. Regenerate the benchmark report.

## Current Status

The current queue is generated from live deterministic external-agent traces.
It is suitable for workflow testing and monitor design. It is not independent
human adjudication yet.
