"""Generate Benchmark v1 with labeled local-agent metrics."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.dataset import load_jsonl
from armour_labs.evals import load_builtin_evals
from armour_labs.metrics import evaluate_labeled_records


DATASET_PATH = ROOT / "datasets" / "local_agent_labeled_traces.jsonl"
BENCHMARK_DIR = ROOT / "benchmarks"
REPORT_PATH = BENCHMARK_DIR / "armour_agent_safety_v1.md"
SUMMARY_PATH = BENCHMARK_DIR / "armour_agent_safety_v1_summary.json"


def main() -> int:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    records = load_jsonl(DATASET_PATH)
    metrics = evaluate_labeled_records(records)
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite": "armour-agent-safety-v1",
        "eval_count": len(load_builtin_evals()),
        "dataset": {
            "path": "datasets/local_agent_labeled_traces.jsonl",
            "records": len(records),
            "label_source": "synthetic-reference",
            "safe_records": sum(1 for record in records if record["label"] == "safe"),
            "risky_records": sum(1 for record in records if record["label"] == "risky"),
        },
        "metrics": {
            "overall": metrics["overall"],
            "by_policy": metrics["by_policy"],
            "by_label": metrics["by_label"],
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(_render_markdown(summary), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    return 0


def _render_markdown(summary: dict[str, Any]) -> str:
    overall = summary["metrics"]["overall"]
    policy_rows = "\n".join(
        _metric_row(policy, metrics) for policy, metrics in summary["metrics"]["by_policy"].items()
    )
    return f"""# Armour Agent Safety Benchmark v1

Generated: {summary["created_at"]}

Benchmark v1 moves beyond simulated profile summaries by evaluating a labeled
local-agent trace dataset. The local agent emits MCP-style JSONL events, Armour
imports those events through the same adapter used for external agent logs, and
the monitor verdicts are scored against reference labels.

## Dataset

- Eval cases: {summary["eval_count"]}
- Labeled trace records: {summary["dataset"]["records"]}
- Safe records: {summary["dataset"]["safe_records"]}
- Risky records: {summary["dataset"]["risky_records"]}
- Dataset path: `{summary["dataset"]["path"]}`
- Label source: `{summary["dataset"]["label_source"]}`

## Overall Monitor Metrics

| Records | TP | FP | TN | FN | Precision | Recall | Specificity | Accuracy | F1 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| {overall["records"]} | {overall["true_positive"]} | {overall["false_positive"]} | {overall["true_negative"]} | {overall["false_negative"]} | {_pct(overall["precision"])} | {_pct(overall["recall"])} | {_pct(overall["specificity"])} | {_pct(overall["accuracy"])} | {_pct(overall["f1"])} |

## Metrics By Local Agent Policy

Policy slices may contain only safe or only risky records, so precision or
recall can be zero when that denominator has no positive examples. Use the
overall row for the primary precision/recall readout.

| Policy | Records | TP | FP | TN | FN | Precision | Recall | Specificity | Accuracy | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{policy_rows}

## What This Proves

- Armour now has a 200-record labeled trace dataset spanning the full 100-eval
  suite.
- The evaluated traces enter through MCP-style event logs rather than direct
  simulator traces.
- The report includes precision, recall, specificity, accuracy, and F1 instead
  of only pass/fail catch-rate.

## Limitations

- Labels are deterministic reference labels from local policies, not independent
  human annotations.
- The local agent is a harness for data generation, not a frontier model.
- Perfect metrics on this dataset should be read as an integration sanity check,
  not as evidence of production monitor accuracy.

## Next Benchmark

Benchmark v2 should add at least one real external agent run, independent human
labels, and false-positive/false-negative review notes.
"""


def _metric_row(name: str, metrics: dict[str, Any]) -> str:
    return (
        f"| `{name}` | {metrics['records']} | {metrics['true_positive']} | "
        f"{metrics['false_positive']} | {metrics['true_negative']} | "
        f"{metrics['false_negative']} | {_pct(metrics['precision'])} | "
        f"{_pct(metrics['recall'])} | {_pct(metrics['specificity'])} | "
        f"{_pct(metrics['accuracy'])} | {_pct(metrics['f1'])} |"
    )


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
