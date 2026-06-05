"""Parse and adjudicate reviewer response CSVs."""

from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from typing import Any

from armour_labs.reviewer_packet import REVIEW_CONFIDENCE, REVIEW_LABELS


TRUE_VALUES = {"true", "yes", "y", "1", "correct"}
FALSE_VALUES = {"false", "no", "n", "0", "incorrect"}
DEFAULT_FIRST_PARTY_REVIEWER_IDS = {"raj_kashikar_2026_06"}
DEFAULT_ANONYMOUS_EXTERNAL_REVIEWER_IDS = {
    "anon_agent_tooling_2026_06",
    "anon_ai_safety_eval_2026_06",
    "anon_enterprise_security_2026_06",
}
CLAIM_READY_DISPOSITIONS = {"consensus", "majority"}


def parse_reviewer_csv(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        if not row.get("review_id"):
            continue
        label = _normalized(row.get("label", ""))
        confidence = _normalized(row.get("confidence", ""))
        reviewer_id = str(row.get("reviewer_id", "")).strip()
        if not reviewer_id or not label:
            continue
        if label not in REVIEW_LABELS:
            raise ValueError(f"Invalid label on line {line_number}: {label}")
        if confidence and confidence not in REVIEW_CONFIDENCE:
            raise ValueError(f"Invalid confidence on line {line_number}: {confidence}")
        rows.append(
            {
                "review_id": str(row["review_id"]).strip(),
                "assignment_id": str(row.get("assignment_id", "")).strip(),
                "reviewer_id": reviewer_id,
                "label": label,
                "confidence": confidence or "unknown",
                "rationale": str(row.get("rationale", "")).strip(),
                "relevant_steps": _parse_steps(str(row.get("relevant_steps", ""))),
                "monitor_verdict_correct": _parse_bool(str(row.get("monitor_verdict_correct", ""))),
                "notes": str(row.get("notes", "")).strip(),
            }
        )
    return rows


def adjudicate_responses(
    review_items: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    minimum_reviewers: int = 2,
    first_party_reviewer_ids: set[str] | None = None,
    anonymous_external_reviewer_ids: set[str] | None = None,
) -> dict[str, Any]:
    first_party_ids = DEFAULT_FIRST_PARTY_REVIEWER_IDS if first_party_reviewer_ids is None else first_party_reviewer_ids
    anonymous_external_ids = (
        DEFAULT_ANONYMOUS_EXTERNAL_REVIEWER_IDS
        if anonymous_external_reviewer_ids is None
        else anonymous_external_reviewer_ids
    )
    items_by_review_id = {item["review_id"]: item for item in review_items}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unknown_review_ids: list[str] = []
    for response in responses:
        if response["review_id"] not in items_by_review_id:
            unknown_review_ids.append(response["review_id"])
            continue
        grouped[response["review_id"]].append(_with_independence(response, first_party_ids, anonymous_external_ids))

    adjudicated: list[dict[str, Any]] = []
    for item in review_items:
        item_responses = grouped.get(item["review_id"], [])
        adjudicated.append(_adjudicate_item(item, item_responses, minimum_reviewers))

    return {
        "summary": _summary(adjudicated, responses, unknown_review_ids, first_party_ids, anonymous_external_ids),
        "items": adjudicated,
        "unknown_review_ids": sorted(set(unknown_review_ids)),
    }


def render_adjudication_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    rows = "\n".join(_row(item) for item in result["items"])
    if not rows:
        rows = "| none | none | none | none | none | none |"
    provenance_note = _provenance_note(summary)
    return f"""# Reviewer Response Adjudication

This report summarizes reviewer coverage, agreement, and reviewer provenance.
{provenance_note}

## Summary

- Review items: {summary["review_items"]}
- Response rows: {summary["response_rows"]}
- Covered items: {summary["covered_items"]}
- Complete items: {summary["complete_items"]}
- Consensus items: {summary["consensus_items"]}
- Disagreement items: {summary["disagreement_items"]}
- First-party response rows: {summary["first_party_response_rows"]}
- Anonymous external response rows: {summary["anonymous_external_response_rows"]}
- External response rows: {summary["external_response_rows"]}
- Claim-eligible external items: {summary["claim_eligible_external_items"]}
- Unknown review IDs: {summary["unknown_review_ids"]}
- Coverage: {_pct(summary["coverage"])}
- Completion: {_pct(summary["completion"])}
- Consensus rate among complete items: {_pct(summary["consensus_rate"])}

## Items

| Review ID | Source Record | Responses | Consensus | Reference | Disposition | Reviewer Labels |
|---|---|---:|---|---|---|---|
{rows}
"""


def _adjudicate_item(
    item: dict[str, Any],
    responses: list[dict[str, Any]],
    minimum_reviewers: int,
) -> dict[str, Any]:
    unique_reviewers = sorted({response["reviewer_id"] for response in responses})
    first_party_reviewers = sorted(
        {response["reviewer_id"] for response in responses if response.get("reviewer_independence") == "first_party"}
    )
    anonymous_external_reviewers = sorted(
        {
            response["reviewer_id"]
            for response in responses
            if response.get("reviewer_independence") == "anonymous_external"
        }
    )
    external_reviewers = sorted(
        {
            response["reviewer_id"]
            for response in responses
            if response.get("reviewer_independence") in {"anonymous_external", "external"}
        }
    )
    label_counts = Counter(response["label"] for response in responses)
    consensus_label = ""
    disposition = "needs_review"
    if len(unique_reviewers) < minimum_reviewers:
        disposition = "insufficient_reviewers"
    elif len(label_counts) == 1:
        consensus_label = next(iter(label_counts))
        disposition = "consensus"
    else:
        top_count = label_counts.most_common(1)[0][1]
        top_labels = sorted(label for label, count in label_counts.items() if count == top_count)
        consensus_label = top_labels[0] if len(top_labels) == 1 else ""
        disposition = "majority" if consensus_label else "disagreement"
    claim_eligible_external_review = (
        len(external_reviewers) >= minimum_reviewers and disposition in CLAIM_READY_DISPOSITIONS
    )
    claim_blocking_reason = ""
    if not claim_eligible_external_review:
        claim_blocking_reason = "internal_or_insufficient_external_reviewers"

    return {
        "review_id": item["review_id"],
        "source_record_id": item["source_record_id"],
        "eval_id": item["eval_id"],
        "priority": item.get("priority", "normal"),
        "reference_label": item.get("reference_label", "unknown"),
        "reviewer_count": len(unique_reviewers),
        "reviewer_ids": unique_reviewers,
        "first_party_reviewer_count": len(first_party_reviewers),
        "first_party_reviewer_ids": first_party_reviewers,
        "anonymous_external_reviewer_count": len(anonymous_external_reviewers),
        "anonymous_external_reviewer_ids": anonymous_external_reviewers,
        "external_reviewer_count": len(external_reviewers),
        "external_reviewer_ids": external_reviewers,
        "label_counts": dict(sorted(label_counts.items())),
        "consensus_label": consensus_label,
        "matches_reference": consensus_label == item.get("reference_label") if consensus_label else None,
        "disposition": disposition,
        "claim_eligible_external_review": claim_eligible_external_review,
        "claim_blocking_reason": claim_blocking_reason,
        "responses": responses,
    }


def _summary(
    adjudicated: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    unknown_review_ids: list[str],
    first_party_reviewer_ids: set[str],
    anonymous_external_reviewer_ids: set[str],
) -> dict[str, Any]:
    covered = [item for item in adjudicated if item["reviewer_count"] > 0]
    complete = [item for item in adjudicated if item["reviewer_count"] >= 2]
    consensus = [item for item in complete if item["disposition"] in {"consensus", "majority"}]
    disagreements = [item for item in complete if item["disposition"] == "disagreement"]
    claim_eligible_external = [item for item in adjudicated if item.get("claim_eligible_external_review")]
    total = len(adjudicated)
    first_party_response_rows = sum(1 for response in responses if response.get("reviewer_id") in first_party_reviewer_ids)
    anonymous_external_response_rows = sum(
        1 for response in responses if response.get("reviewer_id") in anonymous_external_reviewer_ids
    )
    return {
        "review_items": total,
        "response_rows": len(responses),
        "first_party_response_rows": first_party_response_rows,
        "anonymous_external_response_rows": anonymous_external_response_rows,
        "external_response_rows": len(responses) - first_party_response_rows,
        "covered_items": len(covered),
        "complete_items": len(complete),
        "consensus_items": len(consensus),
        "disagreement_items": len(disagreements),
        "claim_eligible_external_items": len(claim_eligible_external),
        "unknown_review_ids": len(set(unknown_review_ids)),
        "coverage": _ratio(len(covered), total),
        "completion": _ratio(len(complete), total),
        "consensus_rate": _ratio(len(consensus), len(complete)),
    }


def _row(item: dict[str, Any]) -> str:
    labels = ", ".join(f"{label}:{count}" for label, count in item["label_counts"].items()) or "none"
    return (
        f"| `{item['review_id']}` | `{item['source_record_id']}` | {item['reviewer_count']} | "
        f"`{item['consensus_label'] or 'none'}` | `{item['reference_label']}` | "
        f"`{item['disposition']}` | {labels} |"
    )


def _normalized(value: str) -> str:
    return value.strip().lower()


def _with_independence(
    response: dict[str, Any],
    first_party_reviewer_ids: set[str],
    anonymous_external_reviewer_ids: set[str],
) -> dict[str, Any]:
    enriched = dict(response)
    reviewer_id = str(response.get("reviewer_id", "")).strip()
    if reviewer_id in first_party_reviewer_ids:
        independence = "first_party"
    elif reviewer_id in anonymous_external_reviewer_ids:
        independence = "anonymous_external"
    else:
        independence = "external"
    enriched["reviewer_independence"] = independence
    return enriched


def _parse_steps(value: str) -> list[int]:
    steps: list[int] = []
    for token in value.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            steps.append(int(token))
        except ValueError:
            continue
    return steps


def _parse_bool(value: str) -> bool | None:
    normalized = _normalized(value)
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return None


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _provenance_note(summary: dict[str, Any]) -> str:
    if summary.get("claim_eligible_external_items", 0):
        return (
            "Anonymous external rows can support trace-review claims when "
            "operator-attested; first-party rows remain calibration only."
        )
    return (
        "Do not use this for external benchmark claims until responses come "
        "from independent external reviewers."
    )
