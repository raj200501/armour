"""Trace dataset provenance and external-claim gates."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from armour_labs.replay import replay_records


MANIFEST_SCHEMA_VERSION = "armour-trace-evidence-manifest-v0"
REQUIRED_RECORD_FIELDS = ("id", "eval_id", "agent_id", "events", "label", "label_source")
CLAIM_BLOCKING_MARKERS = (
    "ci fixture",
    "fixture",
    "internal",
    "local",
    "operator",
    "prompted-reference",
    "synthetic",
)
CLAIM_READY_DISPOSITIONS = {"consensus", "majority"}


def build_trace_evidence_manifest(
    records: list[dict[str, Any]],
    dataset_path: str | Path | None = None,
    *,
    policy_id: str | None = "reviewer-calibrated",
    adjudication: dict[str, Any] | None = None,
    required_model_backed_records: int = 20,
    required_external_reviewed_records: int = 20,
    minimum_reviewers: int = 2,
) -> dict[str, Any]:
    """Build a conservative manifest for public evidence claims."""

    record_ids = [str(record.get("id", "")) for record in records]
    duplicate_ids = sorted(_duplicates(record_ids))
    missing_required = _missing_required_fields(records)
    model_records = [record for record in records if _is_model_backed(record)]
    embedded_reviewed_records = [
        record for record in records if _has_complete_embedded_review(record, minimum_reviewers)
    ]
    embedded_claim_ready_ids = {
        str(record["id"])
        for record in embedded_reviewed_records
        if _record_review_is_claim_ready(record, minimum_reviewers)
    }
    adjudicated_claim_ready_ids = _claim_ready_adjudicated_ids(
        records,
        adjudication or {},
        minimum_reviewers=minimum_reviewers,
    )
    claim_ready_reviewed_ids = sorted(embedded_claim_ready_ids | adjudicated_claim_ready_ids)
    replay = _policy_replay(records, policy_id)

    gates = {
        "schema_complete": not missing_required and not duplicate_ids,
        "model_backed_trace_count": len(model_records) >= required_model_backed_records,
        "external_reviewed_trace_count": len(claim_ready_reviewed_ids) >= required_external_reviewed_records,
        "policy_replay_has_no_errors": replay["errors"] == 0 if replay else True,
    }
    blocked_reasons = _blocked_reasons(
        gates,
        model_records=len(model_records),
        required_model_backed_records=required_model_backed_records,
        claim_ready_reviewed_records=len(claim_ready_reviewed_ids),
        required_external_reviewed_records=required_external_reviewed_records,
        missing_required=missing_required,
        duplicate_ids=duplicate_ids,
        replay_errors=replay["errors"] if replay else 0,
    )

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "path": str(dataset_path) if dataset_path else "in-memory",
            "sha256": _dataset_sha256(records, dataset_path),
            "records": len(records),
            "unique_record_ids": len(set(record_ids)),
            "duplicate_record_ids": duplicate_ids,
            "evals": len({str(record.get("eval_id", "unknown")) for record in records}),
            "required_field_gaps": missing_required,
        },
        "counts": {
            "by_dataset": _count_by(records, "dataset"),
            "by_agent_family": _count_by(records, "agent_family"),
            "by_label": _count_by(records, "label"),
            "by_label_source": _count_by(records, "label_source"),
            "by_review_disposition": _count_by(records, "review_disposition"),
            "by_policy": _count_by(records, "policy"),
            "by_log_format": _count_by(records, "log_format"),
        },
        "evidence": {
            "model_backed_records": len(model_records),
            "model_providers": _model_provider_counts(model_records),
            "model_names": _model_name_counts(model_records),
            "embedded_reviewed_records": len(embedded_reviewed_records),
            "claim_eligible_external_reviewed_records": len(claim_ready_reviewed_ids),
            "claim_eligible_record_ids": claim_ready_reviewed_ids,
            "minimum_reviewers_per_record": minimum_reviewers,
            "adjudication_summary": _adjudication_summary(adjudication or {}),
        },
        "policy_replay": replay,
        "claim_status": {
            "ready_for_external_claim": all(gates.values()),
            "gates": gates,
            "blocked_reasons": blocked_reasons,
            "required_model_backed_records": required_model_backed_records,
            "required_external_reviewed_records": required_external_reviewed_records,
        },
        "recommended_next_actions": _recommended_next_actions(blocked_reasons),
    }


def load_adjudication(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    target = Path(path)
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def _policy_replay(records: list[dict[str, Any]], policy_id: str | None) -> dict[str, Any] | None:
    if not policy_id:
        return None
    replay = replay_records(records, policy_id=policy_id)
    return {
        "policy_pack": replay["policy_pack"],
        "overall": replay["overall"],
        "errors": len(replay["errors"]),
        "changes_from_baseline": len(replay["changes_from_baseline"]),
    }


def _dataset_sha256(records: list[dict[str, Any]], dataset_path: str | Path | None) -> str:
    if dataset_path and Path(dataset_path).exists():
        payload = Path(dataset_path).read_bytes()
    else:
        payload = "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n" for record in records
        ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _missing_required_fields(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        fields = [field for field in REQUIRED_RECORD_FIELDS if field not in record or record[field] in ("", None)]
        if fields:
            missing.append({"index": index, "id": record.get("id", ""), "missing": fields})
    return missing


def _duplicates(values: list[str]) -> set[str]:
    counts = Counter(values)
    return {value for value, count in counts.items() if value and count > 1}


def _count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(str(record.get(key, "unknown")) for record in records)
    return dict(sorted(counts.items()))


def _is_model_backed(record: dict[str, Any]) -> bool:
    family = str(record.get("agent_family", "")).lower()
    return bool(record.get("model_metadata")) or "model-backed" in family or family.startswith("model-")


def _model_provider_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(record.get("model_metadata", {}).get("provider", "unknown")) for record in records)
    return dict(sorted(counts.items()))


def _model_name_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(record.get("model_metadata", {}).get("model", "unknown")) for record in records)
    return dict(sorted(counts.items()))


def _has_complete_embedded_review(record: dict[str, Any], minimum_reviewers: int) -> bool:
    reviewer_ids = _embedded_reviewer_ids(record)
    return (
        len(reviewer_ids) >= minimum_reviewers
        and str(record.get("review_disposition", "")).lower() in CLAIM_READY_DISPOSITIONS
    )


def _record_review_is_claim_ready(record: dict[str, Any], minimum_reviewers: int) -> bool:
    if not _has_complete_embedded_review(record, minimum_reviewers):
        return False
    review_text = " ".join(
        [
            str(record.get("dataset", "")),
            str(record.get("label_source", "")),
            str(record.get("review_disposition", "")),
            str(record.get("review_notes", "")),
            " ".join(_embedded_reviewer_ids(record)),
        ]
    )
    return not _contains_claim_blocking_marker(review_text)


def _embedded_reviewer_ids(record: dict[str, Any]) -> list[str]:
    return sorted({str(review.get("reviewer_id", "")) for review in record.get("reviews", []) if review.get("reviewer_id")})


def _claim_ready_adjudicated_ids(
    records: list[dict[str, Any]],
    adjudication: dict[str, Any],
    *,
    minimum_reviewers: int,
) -> set[str]:
    record_ids = {str(record.get("id", "")) for record in records}
    ready_ids: set[str] = set()
    for item in adjudication.get("items", []):
        source_record_id = str(item.get("source_record_id", ""))
        if source_record_id not in record_ids:
            continue
        if int(item.get("reviewer_count", 0)) < minimum_reviewers:
            continue
        external_count = item.get("external_reviewer_count")
        if external_count is not None and int(external_count) < minimum_reviewers:
            continue
        if str(item.get("disposition", "")).lower() not in CLAIM_READY_DISPOSITIONS:
            continue
        if _adjudication_has_claim_blocking_marker(item):
            continue
        ready_ids.add(source_record_id)
    return ready_ids


def _adjudication_summary(adjudication: dict[str, Any]) -> dict[str, Any]:
    summary = adjudication.get("summary")
    if isinstance(summary, dict):
        return {
            "review_items": summary.get("review_items", 0),
            "complete_items": summary.get("complete_items", 0),
            "consensus_items": summary.get("consensus_items", 0),
            "disagreement_items": summary.get("disagreement_items", 0),
        }
    return {"review_items": 0, "complete_items": 0, "consensus_items": 0, "disagreement_items": 0}


def _contains_claim_blocking_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in CLAIM_BLOCKING_MARKERS)


def _adjudication_has_claim_blocking_marker(item: dict[str, Any]) -> bool:
    """Check provenance markers without blocking trace domains like internal memos."""

    values: list[str] = [
        str(item.get("claim_blocking_reason", "")),
        str(item.get("label_source", "")),
        str(item.get("review_disposition", "")),
    ]
    values.extend(str(value) for value in item.get("reviewer_ids", []))
    values.extend(str(value) for value in item.get("first_party_reviewer_ids", []))
    for response in item.get("responses", []):
        values.append(str(response.get("reviewer_id", "")))
        values.append(str(response.get("reviewer_independence", "")))
    return _contains_claim_blocking_marker(" ".join(values))


def _blocked_reasons(
    gates: dict[str, bool],
    *,
    model_records: int,
    required_model_backed_records: int,
    claim_ready_reviewed_records: int,
    required_external_reviewed_records: int,
    missing_required: list[dict[str, Any]],
    duplicate_ids: list[str],
    replay_errors: int,
) -> list[str]:
    reasons: list[str] = []
    if not gates["schema_complete"]:
        reasons.append(
            f"Dataset schema is incomplete: {len(missing_required)} missing-field records, "
            f"{len(duplicate_ids)} duplicate IDs."
        )
    if not gates["model_backed_trace_count"]:
        reasons.append(
            f"Only {model_records} model-backed records found; need {required_model_backed_records}."
        )
    if not gates["external_reviewed_trace_count"]:
        reasons.append(
            "Only "
            f"{claim_ready_reviewed_records} claim-eligible externally reviewed records found; "
            f"need {required_external_reviewed_records}."
        )
    if not gates["policy_replay_has_no_errors"]:
        reasons.append(f"Policy replay still has {replay_errors} labeled errors.")
    return reasons


def _recommended_next_actions(blocked_reasons: list[str]) -> list[str]:
    if not blocked_reasons:
        return ["Package the manifest, replay artifact, reviewer packet, and benchmark report for external review."]
    actions = []
    for reason in blocked_reasons:
        if "model-backed" in reason:
            actions.append("Run 20-50 real model-backed traces with a rotated local key.")
        elif "externally reviewed" in reason:
            actions.append("Send the blind reviewer queue to independent reviewers and ingest their responses.")
        elif "Policy replay" in reason:
            actions.append("Inspect replay errors before making benchmark claims.")
        elif "schema" in reason.lower():
            actions.append("Fix missing required trace fields and duplicate record IDs before sending packets.")
    return actions
