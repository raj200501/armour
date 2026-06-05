"""Metrics for labeled safety trace datasets."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from armour_labs.adapters import trace_from_agent_events
from armour_labs.runner import scan_trace


RISKY_LABELS = {"risky", "unsafe", "fail"}


def evaluate_labeled_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for record in records:
        trace = trace_from_agent_events(
            record["events"],
            record.get("log_format", "mcp-jsonl"),
            record["eval_id"],
            record["agent_id"],
        )
        report = scan_trace(trace)
        result = report["results"][0]
        expected_risky = str(record["label"]).lower() in RISKY_LABELS
        predicted_risky = result["verdict"] == "fail"
        rows.append(
            {
                "id": record["id"],
                "eval_id": record["eval_id"],
                "agent_id": record["agent_id"],
                "agent_family": record.get("agent_family", "unknown"),
                "policy": record.get("policy", "unknown"),
                "label": record["label"],
                "label_source": record.get("label_source", "unknown"),
                "review_disposition": record.get("review_disposition", "unknown"),
                "reviewer_count": len(record.get("reviews", [])),
                "monitor_expectation": record.get("monitor_expectation", "unspecified"),
                "review_notes": record.get("review_notes", record.get("label_notes", "")),
                "expected_risky": expected_risky,
                "predicted_risky": predicted_risky,
                "verdict": result["verdict"],
                "score": result["score"],
                "finding_count": len(result["findings"]),
                "critical_findings": sum(1 for finding in result["findings"] if finding["severity"] == "critical"),
                "high_findings": sum(1 for finding in result["findings"] if finding["severity"] == "high"),
                "finding_rules": sorted({finding["rule_id"] for finding in result["findings"]}),
            }
        )

    return {
        "overall": _metrics_for_rows(rows),
        "by_policy": _metrics_by_key(rows, "policy"),
        "by_label": _metrics_by_key(rows, "label"),
        "by_label_source": _metrics_by_key(rows, "label_source"),
        "by_agent_family": _metrics_by_key(rows, "agent_family"),
        "errors": [row for row in rows if row["expected_risky"] != row["predicted_risky"]],
        "rows": rows,
    }


def _metrics_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key, "unknown"))].append(row)
    return {name: _metrics_for_rows(group_rows) for name, group_rows in sorted(grouped.items())}


def _metrics_for_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter()
    for row in rows:
        expected = row["expected_risky"]
        predicted = row["predicted_risky"]
        if expected and predicted:
            counts["tp"] += 1
        elif not expected and predicted:
            counts["fp"] += 1
        elif expected and not predicted:
            counts["fn"] += 1
        else:
            counts["tn"] += 1

    total = len(rows)
    precision = _ratio(counts["tp"], counts["tp"] + counts["fp"])
    recall = _ratio(counts["tp"], counts["tp"] + counts["fn"])
    specificity = _ratio(counts["tn"], counts["tn"] + counts["fp"])
    accuracy = _ratio(counts["tp"] + counts["tn"], total)
    f1 = _ratio(2 * precision * recall, precision + recall)

    return {
        "records": total,
        "true_positive": counts["tp"],
        "false_positive": counts["fp"],
        "true_negative": counts["tn"],
        "false_negative": counts["fn"],
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "accuracy": round(accuracy, 4),
        "f1": round(f1, 4),
    }


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
