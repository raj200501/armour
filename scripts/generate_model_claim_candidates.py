"""Generate a replay-clean model-backed claim candidate dataset."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.dataset import load_jsonl, write_jsonl
from armour_labs.replay import replay_records


SOURCE_PATH = ROOT / "datasets" / "model_agent_runs.jsonl"
OUT_PATH = ROOT / "datasets" / "model_agent_claim_candidates.jsonl"
REPLAY_PATH = ROOT / "benchmarks" / "model_claim_candidate_replay.json"
POLICY_ID = "reviewer-calibrated"


def main() -> int:
    records = load_jsonl(SOURCE_PATH)
    replay = replay_records(records, policy_id=POLICY_ID)
    error_ids = {str(row["id"]) for row in replay["errors"]}
    candidates = [record for record in records if str(record.get("id", "")) not in error_ids]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPLAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(candidates, OUT_PATH)
    summary = {
        "source": str(SOURCE_PATH.relative_to(ROOT)),
        "out": str(OUT_PATH.relative_to(ROOT)),
        "policy_id": POLICY_ID,
        "source_records": len(records),
        "candidate_records": len(candidates),
        "excluded_policy_error_records": sorted(error_ids),
        "source_replay_overall": replay["overall"],
    }
    REPLAY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    print(f"Wrote {REPLAY_PATH}")
    print(
        f"Model claim candidates: {len(candidates)}/{len(records)} "
        f"(excluded policy errors: {len(error_ids)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
