"""Replay labeled trace datasets under configurable policy packs."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from armour_labs.adapters import trace_from_agent_events
from armour_labs.evals import get_eval
from armour_labs.metrics import RISKY_LABELS
from armour_labs.monitors import analyze_trace
from armour_labs.policy_packs import (
    BASELINE_POLICY,
    PolicyPack,
    apply_policy_pack,
    get_policy_pack,
    policy_risk_level,
    policy_score,
    policy_verdict,
)


def replay_records(records: list[dict[str, Any]], policy_id: str = "baseline") -> dict[str, Any]:
    policy = get_policy_pack(policy_id)
    rows = [_row_for_record(record, policy) for record in records]
    baseline_rows = [_row_for_record(record, BASELINE_POLICY) for record in records]
    baseline_by_id = {row["id"]: row for row in baseline_rows}
    changes = [
        _change_row(row, baseline_by_id[row["id"]])
        for row in rows
        if row["predicted_risky"] != baseline_by_id[row["id"]]["predicted_risky"]
        or row["finding_rules"] != baseline_by_id[row["id"]]["finding_rules"]
    ]
    return {
        "policy_pack": policy.id,
        "policy_title": policy.title,
        "overall": _metrics_for_rows(rows),
        "by_label": _metrics_by_key(rows, "label"),
        "by_policy": _metrics_by_key(rows, "agent_policy"),
        "errors": [row for row in rows if row["expected_risky"] != row["predicted_risky"]],
        "changes_from_baseline": changes,
        "rows": rows,
    }


def compare_policy_packs(records: list[dict[str, Any]], policy_ids: list[str]) -> dict[str, Any]:
    return {
        "policies": {
            policy_id: replay_records(records, policy_id)["overall"]
            for policy_id in policy_ids
        },
        "policy_order": policy_ids,
    }


def _row_for_record(record: dict[str, Any], policy: PolicyPack) -> dict[str, Any]:
    trace = trace_from_agent_events(
        record["events"],
        record.get("log_format", "mcp-jsonl"),
        record["eval_id"],
        record["agent_id"],
    )
    eval_case = get_eval(trace.eval_id)
    baseline_findings = analyze_trace(eval_case, trace)
    findings = apply_policy_pack(eval_case, trace, baseline_findings, policy)
    expected_risky = str(record["label"]).lower() in RISKY_LABELS
    verdict = policy_verdict(findings, policy)
    return {
        "id": record["id"],
        "eval_id": trace.eval_id,
        "agent_id": trace.agent_id,
        "agent_family": record.get("agent_family", "unknown"),
        "agent_policy": record.get("policy", "unknown"),
        "label": record["label"],
        "label_source": record.get("label_source", "unknown"),
        "expected_risky": expected_risky,
        "predicted_risky": verdict == "fail",
        "verdict": verdict,
        "risk_level": policy_risk_level(findings),
        "score": policy_score(findings),
        "finding_rules": sorted({finding.rule_id for finding in findings}),
        "findings": [finding.to_dict() for finding in findings],
    }


def _change_row(row: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "label": row["label"],
        "baseline_predicted_risky": baseline["predicted_risky"],
        "policy_predicted_risky": row["predicted_risky"],
        "baseline_rules": baseline["finding_rules"],
        "policy_rules": row["finding_rules"],
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
