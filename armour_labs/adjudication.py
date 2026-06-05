"""Adjudication helpers for monitor and judge disagreements."""

from __future__ import annotations

from typing import Any

from armour_labs.judge_baseline import evaluate_judge
from armour_labs.metrics import evaluate_labeled_records


def build_adjudication_queue(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    monitor = evaluate_labeled_records(records)
    judge = evaluate_judge(records)
    judge_by_id = {row["id"]: row for row in judge["rows"]}
    queue: list[dict[str, Any]] = []
    for row in monitor["rows"]:
        judge_row = judge_by_id[row["id"]]
        needs_review = (
            row["expected_risky"] != row["predicted_risky"]
            or judge_row["expected_risky"] != judge_row["predicted_risky"]
            or row["predicted_risky"] != judge_row["predicted_risky"]
        )
        if not needs_review:
            continue
        queue.append(
            {
                "id": row["id"],
                "eval_id": row["eval_id"],
                "label": row["label"],
                "monitor_verdict": row["verdict"],
                "monitor_predicted_risky": row["predicted_risky"],
                "judge_predicted_risky": judge_row["predicted_risky"],
                "finding_rules": row["finding_rules"],
                "judge_rationale": judge_row["rationale"],
                "review_notes": row["review_notes"],
                "adjudication_reason": _reason(row, judge_row),
            }
        )
    return queue


def _reason(monitor_row: dict[str, Any], judge_row: dict[str, Any]) -> str:
    if monitor_row["expected_risky"] != monitor_row["predicted_risky"]:
        return "monitor_label_disagreement"
    if judge_row["expected_risky"] != judge_row["predicted_risky"]:
        return "judge_label_disagreement"
    return "monitor_judge_disagreement"
