"""Dataset helpers for labeled agent-log records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from armour_labs.evals import load_builtin_evals
from armour_labs.local_agent import LOCAL_AGENT_POLICIES, generate_local_agent_events, reference_label_for_policy


DATASET_VERSION = "armour-local-agent-labels-v0"


def build_local_agent_dataset(limit: int | None = None) -> list[dict[str, Any]]:
    evals = load_builtin_evals()
    records: list[dict[str, Any]] = []
    for eval_case in evals:
        for policy in LOCAL_AGENT_POLICIES:
            record_id = f"{eval_case.id}:{policy}"
            records.append(
                {
                    "id": record_id,
                    "dataset": DATASET_VERSION,
                    "eval_id": eval_case.id,
                    "agent_id": f"local-{policy}-agent",
                    "policy": policy,
                    "label": reference_label_for_policy(policy),
                    "label_source": "synthetic-reference",
                    "label_notes": (
                        "Reference label generated from a deterministic local agent policy. "
                        "Replace with independent human labels before making external claims."
                    ),
                    "log_format": "mcp-jsonl",
                    "events": generate_local_agent_events(eval_case, policy),
                }
            )
    if limit is not None:
        return records[:limit]
    return records


def write_jsonl(records: Iterable[dict[str, Any]], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
