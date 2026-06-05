"""External evidence gate status for model-backed and reviewer claims."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


EXTERNAL_GATE_SCHEMA_VERSION = "armour-external-gate-status-v0"


def build_external_gate_status(manifest: dict[str, Any]) -> dict[str, Any]:
    claim_status = manifest.get("claim_status", {})
    evidence = manifest.get("evidence", {})
    required_model = int(claim_status.get("required_model_backed_records", 20))
    required_reviewed = int(claim_status.get("required_external_reviewed_records", 20))
    current_model = int(evidence.get("model_backed_records", 0))
    current_reviewed = int(evidence.get("claim_eligible_external_reviewed_records", 0))
    model_gap = max(0, required_model - current_model)
    reviewed_gap = max(0, required_reviewed - current_reviewed)

    return {
        "schema_version": EXTERNAL_GATE_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ready_for_external_claim": bool(claim_status.get("ready_for_external_claim", False)),
        "gates": claim_status.get("gates", {}),
        "counts": {
            "model_backed_records": current_model,
            "claim_eligible_external_reviewed_records": current_reviewed,
            "required_model_backed_records": required_model,
            "required_external_reviewed_records": required_reviewed,
            "model_backed_gap": model_gap,
            "external_review_gap": reviewed_gap,
        },
        "claim_eligible_record_ids": evidence.get("claim_eligible_record_ids", []),
        "blocked_reasons": claim_status.get("blocked_reasons", []),
        "provider_coverage": {
            "model_providers": evidence.get("model_providers", {}),
            "model_names": evidence.get("model_names", {}),
        },
        "clearance_plan": _clearance_plan(model_gap, reviewed_gap),
        "claim_discipline": [
            "Do not count dry-run, fixture, internal, operator, or prompted-reference labels as external proof.",
            "Anonymous external reviews can count when operator-attested, but named/public reviewer evidence is stronger.",
            "Do not serialize API keys in datasets, reports, commands, PR text, or tracked env files.",
            "Do not claim external validation until both gate counts meet the threshold.",
        ],
    }


def render_external_gate_status_markdown(status: dict[str, Any]) -> str:
    counts = status["counts"]
    gate_rows = "\n".join(
        f"| `{name}` | `{passed}` |" for name, passed in sorted(status.get("gates", {}).items())
    )
    if not gate_rows:
        gate_rows = "| none | false |"
    blockers = "\n".join(f"- {reason}" for reason in status.get("blocked_reasons", []))
    if not blockers:
        blockers = "- none"
    model_steps = "\n".join(f"{index}. {step}" for index, step in enumerate(status["clearance_plan"]["model_steps"], start=1))
    review_steps = "\n".join(
        f"{index}. {step}" for index, step in enumerate(status["clearance_plan"]["reviewer_steps"], start=1)
    )
    return f"""# External Claim Gate Status

Generated: {status["generated_at"]}

This artifact tracks whether Armour has enough real evidence for
public external claims. It is intentionally conservative.

## Current Counts

- Model-backed records: {counts["model_backed_records"]}/{counts["required_model_backed_records"]}
- Claim-eligible externally reviewed records: {counts["claim_eligible_external_reviewed_records"]}/{counts["required_external_reviewed_records"]}
- Model-backed record gap: {counts["model_backed_gap"]}
- External review gap: {counts["external_review_gap"]}
- Ready for external claim: `{status["ready_for_external_claim"]}`

## Gates

| Gate | Passed |
|---|---|
{gate_rows}

## Blockers

{blockers}

## Model Clearance Steps

{model_steps}

## Reviewer Clearance Steps

{review_steps}

## Claim Discipline

{_claim_discipline_lines(status)}
"""


def _clearance_plan(model_gap: int, reviewed_gap: int) -> dict[str, list[str]]:
    model_steps = [
        "Set a local process environment key for Gemini, Anthropic, or an OpenAI-compatible endpoint.",
        "Run `python3 scripts/run_model_agent_benchmark.py --provider <provider> --model \"$MODEL\" --limit 20`.",
        "Run `python3 -m armour_labs.cli trace-manifest datasets/model_agent_runs.jsonl --out benchmarks/trace_evidence_manifest_model.json`.",
    ]
    if model_gap == 0:
        model_steps = ["Model-backed trace threshold is met; keep provider/model provenance in the manifest."]

    reviewer_steps = [
        "Send the blind reviewer packet and response template to independent reviewers.",
        "Collect at least two independent external reviewer rows per claim-target trace.",
        "Run `python3 scripts/process_reviewer_responses.py --responses <external-response.csv>`.",
        "Run `python3 scripts/generate_reviewer_intake.py` to verify first-party and external reviewer counts.",
        "Rebuild `python3 -m armour_labs.cli trace-manifest datasets/model_agent_claim_candidates.jsonl --adjudication review/reviewer_adjudication.json`.",
    ]
    if reviewed_gap == 0:
        reviewer_steps = ["External review threshold is met; preserve adjudication provenance for the data room."]

    return {"model_steps": model_steps, "reviewer_steps": reviewer_steps}


def _claim_discipline_lines(status: dict[str, Any]) -> str:
    return "\n".join(f"- {item}" for item in status.get("claim_discipline", []))
