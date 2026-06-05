"""Generate Benchmark v2 with reviewed external-style traces and error analysis."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.dataset import load_jsonl
from armour_labs.metrics import evaluate_labeled_records


LOCAL_DATASET_PATH = ROOT / "datasets" / "local_agent_labeled_traces.jsonl"
REVIEWED_DATASET_PATH = ROOT / "datasets" / "reviewed_external_agent_traces.jsonl"
BENCHMARK_DIR = ROOT / "benchmarks"
REPORT_PATH = BENCHMARK_DIR / "armour_agent_safety_v2.md"
SUMMARY_PATH = BENCHMARK_DIR / "armour_agent_safety_v2_summary.json"


def main() -> int:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    local_records = load_jsonl(LOCAL_DATASET_PATH)
    reviewed_records = load_jsonl(REVIEWED_DATASET_PATH)
    local_metrics = evaluate_labeled_records(local_records)
    reviewed_metrics = evaluate_labeled_records(reviewed_records)
    combined_metrics = evaluate_labeled_records([*local_records, *reviewed_records])
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite": "armour-agent-safety-v2",
        "datasets": {
            "local_reference": {
                "path": "datasets/local_agent_labeled_traces.jsonl",
                "records": len(local_records),
                "label_source": "synthetic-reference",
                "metrics": local_metrics["overall"],
            },
            "reviewed_external_fixtures": {
                "path": "datasets/reviewed_external_agent_traces.jsonl",
                "records": len(reviewed_records),
                "label_source": "dual-review-fixture",
                "metrics": reviewed_metrics["overall"],
                "by_agent_family": reviewed_metrics["by_agent_family"],
                "errors": reviewed_metrics["errors"],
            },
        },
        "combined_metrics": combined_metrics["overall"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(_render_markdown(summary), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    return 0


def _render_markdown(summary: dict[str, Any]) -> str:
    local = summary["datasets"]["local_reference"]
    reviewed = summary["datasets"]["reviewed_external_fixtures"]
    combined = summary["combined_metrics"]
    family_rows = "\n".join(
        _metric_row(name, metrics) for name, metrics in reviewed["by_agent_family"].items()
    )
    error_rows = "\n".join(_error_row(error) for error in reviewed["errors"])
    if not error_rows:
        error_rows = "| none | none | none | none | none |"
    return f"""# Armour Agent Safety Benchmark v2

Generated: {summary["created_at"]}

Benchmark v2 adds reviewed external-style MCP traces and explicit error
analysis. This is still not a frontier-model benchmark: the reviewed external
traces are recorded fixtures with consensus review labels. The purpose is to
exercise the review workflow, expose monitor gaps, and make the next data
collection step concrete.

## Dataset Summary

| Dataset | Records | Label Source | Precision | Recall | Specificity | Accuracy | F1 |
|---|---:|---|---:|---:|---:|---:|---:|
| local reference | {local["records"]} | `{local["label_source"]}` | {_pct(local["metrics"]["precision"])} | {_pct(local["metrics"]["recall"])} | {_pct(local["metrics"]["specificity"])} | {_pct(local["metrics"]["accuracy"])} | {_pct(local["metrics"]["f1"])} |
| reviewed external fixtures | {reviewed["records"]} | `{reviewed["label_source"]}` | {_pct(reviewed["metrics"]["precision"])} | {_pct(reviewed["metrics"]["recall"])} | {_pct(reviewed["metrics"]["specificity"])} | {_pct(reviewed["metrics"]["accuracy"])} | {_pct(reviewed["metrics"]["f1"])} |
| combined | {combined["records"]} | mixed | {_pct(combined["precision"])} | {_pct(combined["recall"])} | {_pct(combined["specificity"])} | {_pct(combined["accuracy"])} | {_pct(combined["f1"])} |

## Reviewed External Metrics By Agent Family

| Agent Family | Records | TP | FP | TN | FN | Precision | Recall | Specificity | Accuracy | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{family_rows}

## False Positive / False Negative Review Notes

| Record | Label | Verdict | Finding Rules | Expected Issue | Review Notes |
|---|---|---|---|---|---|
{error_rows}

## What This Adds

- Reviewed external-style MCP traces are scored separately from local reference
  traces.
- Each reviewed fixture has two consensus review records.
- Benchmark v2 reports false-positive and false-negative cases instead of
  hiding them behind aggregate metrics.
- The current hard cases expose two concrete monitor gaps: negation-aware
  credential handling and subtle data-minimization overreach.

## Limitations

- Reviewed external traces are fixtures, not live frontier-agent runs.
- Review labels are repo artifacts created for workflow validation, not an
  independent human study.
- The metrics are useful for regression and monitor design, not for external
  product claims.

## Next Benchmark

Benchmark v3 should import at least one live external agent run, add independent
human reviewers, and compare rule monitors against an LLM-judge baseline.
"""


def _metric_row(name: str, metrics: dict[str, Any]) -> str:
    return (
        f"| `{name}` | {metrics['records']} | {metrics['true_positive']} | "
        f"{metrics['false_positive']} | {metrics['true_negative']} | "
        f"{metrics['false_negative']} | {_pct(metrics['precision'])} | "
        f"{_pct(metrics['recall'])} | {_pct(metrics['specificity'])} | "
        f"{_pct(metrics['accuracy'])} | {_pct(metrics['f1'])} |"
    )


def _error_row(row: dict[str, Any]) -> str:
    rules = ", ".join(row["finding_rules"]) if row["finding_rules"] else "none"
    return (
        f"| `{row['id']}` | `{row['label']}` | `{row['verdict']}` | "
        f"{rules} | `{row['monitor_expectation']}` | {_clean(row['review_notes'])} |"
    )


def _clean(text: str) -> str:
    return " ".join(text.split()).replace("|", "/")


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
