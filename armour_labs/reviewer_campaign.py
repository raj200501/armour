"""Reviewer recruitment and assignment campaign artifacts."""

from __future__ import annotations

import csv
import io
from typing import Any


DEFAULT_REVIEWER_ROLES = (
    ("ai_safety_researcher", "methodology critique and risk-label quality"),
    ("agent_security_engineer", "tool-use boundary and abuse-case review"),
    ("mcp_tool_builder", "trace realism and integration feedback"),
    ("applied_ml_eval_engineer", "eval design and baseline comparison feedback"),
    ("security_researcher", "data exfiltration and credential-boundary review"),
)

RESPONSE_TEMPLATE_FIELDS = [
    "assignment_id",
    "review_id",
    "reviewer_id",
    "label",
    "confidence",
    "rationale",
    "relevant_steps",
    "monitor_verdict_correct",
    "notes",
]

PRESERVED_RESPONSE_FIELDS = [
    "reviewer_id",
    "label",
    "confidence",
    "rationale",
    "relevant_steps",
    "monitor_verdict_correct",
    "notes",
]

ASSIGNMENT_MATRIX_FIELDS = [
    "assignment_id",
    "review_id",
    "source_record_id",
    "eval_id",
    "priority",
    "reviewer_slot",
    "assigned_reviewer_id",
    "reviewer_email",
    "status",
]

PRESERVED_ASSIGNMENT_FIELDS = [
    "assigned_reviewer_id",
    "reviewer_email",
    "status",
]

RECRUITMENT_TRACKER_FIELDS = [
    "target_id",
    "role",
    "name",
    "email",
    "source",
    "ask",
    "success_signal",
    "status",
    "sent_at",
    "reply_at",
    "next_action",
]

PRESERVED_TRACKER_FIELDS = [
    "name",
    "email",
    "source",
    "status",
    "sent_at",
    "reply_at",
    "next_action",
]


def assignment_rows(items: list[dict[str, Any]], reviewers_per_item: int = 2) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        for slot in range(1, reviewers_per_item + 1):
            rows.append(
                {
                    "assignment_id": f"{item['review_id']}:r{slot}",
                    "review_id": item["review_id"],
                    "source_record_id": item["source_record_id"],
                    "eval_id": item["eval_id"],
                    "priority": item.get("priority", "normal"),
                    "reviewer_slot": f"reviewer_{slot}",
                    "assigned_reviewer_id": "",
                    "reviewer_email": "",
                    "status": "planned",
                }
            )
    return rows


def assignment_matrix_csv(items: list[dict[str, Any]], reviewers_per_item: int = 2) -> str:
    rows = assignment_rows(items, reviewers_per_item=reviewers_per_item)
    return _csv(rows, ASSIGNMENT_MATRIX_FIELDS)


def merge_assignment_matrix_csv(generated_csv: str, existing_csv: str) -> str:
    return _merge_csv_by_key(
        generated_csv,
        existing_csv,
        key_field="assignment_id",
        fieldnames=ASSIGNMENT_MATRIX_FIELDS,
        preserved_fields=PRESERVED_ASSIGNMENT_FIELDS,
    )


def two_reviewer_response_template_csv(items: list[dict[str, Any]], reviewers_per_item: int = 2) -> str:
    rows = []
    for assignment in assignment_rows(items, reviewers_per_item=reviewers_per_item):
        rows.append(
            {
                "assignment_id": assignment["assignment_id"],
                "review_id": assignment["review_id"],
                "reviewer_id": "",
                "label": "",
                "confidence": "",
                "rationale": "",
                "relevant_steps": "",
                "monitor_verdict_correct": "",
                "notes": "",
            }
        )
    return _csv(rows, RESPONSE_TEMPLATE_FIELDS)


def merge_response_template_csv(generated_csv: str, existing_csv: str) -> str:
    """Preserve completed reviewer cells when regenerating assignment rows."""

    return _merge_csv_by_key(
        generated_csv,
        existing_csv,
        key_field="assignment_id",
        fieldnames=RESPONSE_TEMPLATE_FIELDS,
        preserved_fields=PRESERVED_RESPONSE_FIELDS,
    )


def recruitment_tracker_csv(target_count: int = 10) -> str:
    rows = []
    roles = list(DEFAULT_REVIEWER_ROLES)
    for index in range(1, target_count + 1):
        role, success_signal = roles[(index - 1) % len(roles)]
        rows.append(
            {
                "target_id": f"reviewer-target-{index:02d}",
                "role": role,
                "name": "",
                "email": "",
                "source": "",
                "ask": "review 5-10 blind model-backed traces",
                "success_signal": success_signal,
                "status": "not_contacted",
                "sent_at": "",
                "reply_at": "",
                "next_action": "identify contact and send reviewer ask",
            }
        )
    return _csv(rows, RECRUITMENT_TRACKER_FIELDS)


def merge_recruitment_tracker_csv(generated_csv: str, existing_csv: str) -> str:
    return _merge_csv_by_key(
        generated_csv,
        existing_csv,
        key_field="target_id",
        fieldnames=RECRUITMENT_TRACKER_FIELDS,
        preserved_fields=PRESERVED_TRACKER_FIELDS,
    )


def campaign_summary(items: list[dict[str, Any]], reviewers_per_item: int = 2, target_count: int = 10) -> dict[str, Any]:
    return {
        "review_items": len(items),
        "reviewers_per_item": reviewers_per_item,
        "required_response_rows": len(items) * reviewers_per_item,
        "reviewer_targets": target_count,
        "claim_target_items": min(20, len(items)),
        "status": "ready_to_send_reviewer_asks",
        "blocked_on": "real independent reviewer responses",
    }


def external_reviewer_response_template_csv(items: list[dict[str, Any]], reviewers_per_item: int = 2) -> str:
    rows = []
    for item in items:
        for slot in range(1, reviewers_per_item + 1):
            rows.append(
                {
                    "assignment_id": f"{item['review_id']}:external-r{slot}",
                    "review_id": item["review_id"],
                    "reviewer_id": "",
                    "label": "",
                    "confidence": "",
                    "rationale": "",
                    "relevant_steps": "",
                    "monitor_verdict_correct": "",
                    "notes": "",
                }
            )
    return _csv(rows, RESPONSE_TEMPLATE_FIELDS)


def render_email_drafts(summary: dict[str, Any]) -> str:
    return f"""# Reviewer Outreach Drafts

Use these drafts for external review requests. Do not ask for funding,
hiring, or partnership yet. The ask is trace-labeling feedback.

## Current Ask

- Review items: {summary["review_items"]}
- Required response rows: {summary["required_response_rows"]}
- Reviewer targets to identify: {summary["reviewer_targets"]}
- Blocked on: {summary["blocked_on"]}

## Short Reviewer Ask

Subject: Quick review request: AI agent safety traces

Hi <name>,

I am building Armour, a small open benchmark for auditing tool-using AI agent
traces. I have a set of real model-backed traces and need independent labels
before making any public claims.

Would you be willing to review 5-10 short blind traces and label each as safe,
risky, or uncertain? The packet includes the trace steps and a CSV response
template. Please use the external reviewer template rather than any internal or
first-party calibration rows. I am mainly looking for methodology feedback and
disagreement with my labels.

Packet: <link>
Instructions: <link to reviewer handoff prompt>

Thanks,
<your name>

## Technical Feedback Ask

Subject: Feedback on model-backed agent safety benchmark

Hi <name>,

I am testing whether a lightweight trace auditor can catch risky behavior in
tool-using AI agents: data overreach, credential-boundary violations, policy
bypass, audit tampering, false completion, and unsafe autonomy.

The current packet uses real Gemini-backed traces and a replay-clean candidate
set. Would you be open to reviewing a few traces or critiquing the labeling
guide?

I am not asking for hiring or partnership conversations. I am trying to make
the evaluation credible before broader publication.

Thanks,
<your name>

## Follow-Up

Subject: Re: Quick review request: AI agent safety traces

Hi <name>,

Following up once. The review should take about 10-15 minutes for a small
sample. Even a short note on whether the labels or trace format seem useful
would help.

Thanks,
<your name>
"""


def _csv(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def _merge_csv_by_key(
    generated_csv: str,
    existing_csv: str,
    *,
    key_field: str,
    fieldnames: list[str],
    preserved_fields: list[str],
) -> str:
    generated_rows = list(csv.DictReader(io.StringIO(generated_csv)))
    existing_rows = list(csv.DictReader(io.StringIO(existing_csv)))
    existing_by_key = {
        str(row.get(key_field, "")).strip(): row
        for row in existing_rows
        if str(row.get(key_field, "")).strip()
    }

    for row in generated_rows:
        row_key = str(row.get(key_field, "")).strip()
        existing = existing_by_key.get(row_key)
        if not existing or not any(str(existing.get(field, "")).strip() for field in preserved_fields):
            continue
        for field in preserved_fields:
            row[field] = existing.get(field, row.get(field, ""))

    return _csv(generated_rows, fieldnames)
