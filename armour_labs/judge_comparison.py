"""Compare Armour monitor results against generic judge baselines."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from armour_labs.judge_baseline import evaluate_judge
from armour_labs.metrics import RISKY_LABELS
from armour_labs.replay import replay_records


JUDGE_COMPARISON_SCHEMA_VERSION = "armour-judge-comparison-v0"


def claim_target_records(records: list[dict[str, Any]], adjudication: dict[str, Any]) -> list[dict[str, Any]]:
    """Return claim-target records relabeled with external consensus labels."""

    labels = {
        item["source_record_id"]: item.get("consensus_label")
        for item in adjudication.get("items", [])
        if item.get("claim_eligible_external_review") and item.get("consensus_label")
    }
    relabeled: list[dict[str, Any]] = []
    for record in records:
        consensus_label = labels.get(record.get("id"))
        if not consensus_label:
            continue
        candidate = dict(record)
        candidate["label"] = consensus_label
        candidate["label_source"] = "anonymous-external-consensus"
        relabeled.append(candidate)
    return relabeled


def build_judge_comparison(
    records: list[dict[str, Any]],
    adjudication: dict[str, Any],
    *,
    model_predictions: dict[str, Any] | None = None,
    policy_id: str = "reviewer-calibrated",
) -> dict[str, Any]:
    targets = claim_target_records(records, adjudication)
    armour = replay_records(targets, policy_id)
    generic_judge = evaluate_judge(targets)
    baselines = {
        "armour_reviewer_calibrated": {
            "kind": "rule-monitor-policy-pack",
            "metrics": armour["overall"],
            "errors": armour["errors"],
        },
        "generic_llm_judge_proxy": {
            "kind": "offline-rubric-proxy",
            "metrics": generic_judge["overall"],
            "errors": generic_judge["errors"],
            "limitation": "Offline proxy with an LLM-judge-style interface; not a live model call.",
        },
    }
    model_judge = _score_model_predictions(targets, model_predictions or {})
    if model_judge:
        baselines["model_judge"] = model_judge

    generic_metrics = baselines["generic_llm_judge_proxy"]["metrics"]
    armour_metrics = baselines["armour_reviewer_calibrated"]["metrics"]
    return {
        "schema_version": JUDGE_COMPARISON_SCHEMA_VERSION,
        "record_count": len(targets),
        "policy_id": policy_id,
        "baselines": baselines,
        "deltas": {
            "armour_minus_generic_proxy": _metric_delta(armour_metrics, generic_metrics),
        },
        "generic_proxy_missed_risky_records": [
            row["id"]
            for row in generic_judge["errors"]
            if row["expected_risky"] and not row["predicted_risky"]
        ],
        "armour_error_records": [row["id"] for row in armour["errors"]],
        "label_distribution": dict(Counter(record["label"] for record in targets)),
        "interpretation": _interpretation(armour_metrics, generic_metrics),
    }


def render_judge_comparison_markdown(report: dict[str, Any]) -> str:
    baselines = report["baselines"]
    rows = "\n".join(
        _metrics_row(name, baseline["kind"], baseline["metrics"])
        for name, baseline in baselines.items()
    )
    misses = "\n".join(f"- `{record_id}`" for record_id in report["generic_proxy_missed_risky_records"]) or "- none"
    limitations = "\n".join(
        f"- `{name}`: {baseline['limitation']}"
        for name, baseline in baselines.items()
        if baseline.get("limitation")
    ) or "- none"
    delta = report["deltas"]["armour_minus_generic_proxy"]
    return f"""# Model-Claim Judge Comparison

This artifact compares Armour's reviewer-calibrated trace monitor against a
generic LLM-judge-style baseline on the anonymous-reviewed model-backed claim
traces. The default generic judge is an offline rubric proxy; real model-judge
predictions can be supplied separately and are scored with the same shape.

## Summary

- Claim-target records: {report["record_count"]}
- Policy: `{report["policy_id"]}`
- Armour accuracy delta vs generic proxy: {delta["accuracy"]:+.4f}
- Armour recall delta vs generic proxy: {delta["recall"]:+.4f}
- Armour F1 delta vs generic proxy: {delta["f1"]:+.4f}

## Metrics

| Baseline | Kind | Records | TP | FP | TN | FN | Precision | Recall | Specificity | Accuracy | F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{rows}

## Generic Proxy Missed Risky Records

{misses}

## Limitations

{limitations}

## Interpretation

{report["interpretation"]}
"""


def load_model_predictions(path: str | Path) -> dict[str, Any]:
    prediction_path = Path(path)
    if not prediction_path.exists():
        return {}
    return json.loads(prediction_path.read_text(encoding="utf-8"))


def _score_model_predictions(records: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any] | None:
    predictions = payload.get("predictions") or []
    if not predictions:
        return None
    by_id = {str(prediction.get("id")): prediction for prediction in predictions}
    rows = []
    for record in records:
        prediction = by_id.get(record["id"])
        if prediction is None:
            continue
        expected_risky = str(record["label"]).lower() in RISKY_LABELS
        predicted_risky = bool(prediction.get("predicted_risky"))
        rows.append(
            {
                "id": record["id"],
                "label": record["label"],
                "expected_risky": expected_risky,
                "predicted_risky": predicted_risky,
                "confidence": prediction.get("confidence", "unknown"),
                "rationale": prediction.get("rationale", ""),
            }
        )
    if not rows:
        return None
    return {
        "kind": "live-model-judge",
        "metrics": _metrics_for_rows(rows),
        "errors": [row for row in rows if row["expected_risky"] != row["predicted_risky"]],
        "prediction_count": len(rows),
    }


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


def _metric_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, float]:
    return {
        key: round(float(left.get(key, 0.0)) - float(right.get(key, 0.0)), 4)
        for key in ("precision", "recall", "specificity", "accuracy", "f1")
    }


def _metrics_row(name: str, kind: str, metrics: dict[str, Any]) -> str:
    return (
        f"| `{name}` | `{kind}` | {metrics['records']} | {metrics['true_positive']} | "
        f"{metrics['false_positive']} | {metrics['true_negative']} | {metrics['false_negative']} | "
        f"{metrics['precision']:.4f} | {metrics['recall']:.4f} | {metrics['specificity']:.4f} | "
        f"{metrics['accuracy']:.4f} | {metrics['f1']:.4f} |"
    )


def _interpretation(armour: dict[str, Any], generic: dict[str, Any]) -> str:
    if armour.get("false_negative", 0) < generic.get("false_negative", 0):
        return (
            "On this claim-target set, Armour catches risky tool-use traces that the generic "
            "judge proxy misses. This supports the trace-level safety-evaluation wedge while "
            "remaining explicit that a live model-judge baseline is a stronger future artifact."
        )
    return (
        "Armour does not currently beat the generic judge proxy on false negatives; use the "
        "error rows to improve policy coverage before making comparative claims."
    )


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
