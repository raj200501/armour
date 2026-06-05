"""Generate outcome-state report for model-backed claim candidates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.dataset import load_jsonl
from armour_labs.outcome_state import build_outcome_state_report, render_outcome_state_markdown


DATASET_PATH = ROOT / "datasets" / "model_agent_claim_candidates.jsonl"
OUT_JSON_PATH = ROOT / "benchmarks" / "outcome_state_model_claim_candidates.json"
OUT_MD_PATH = ROOT / "benchmarks" / "outcome_state_model_claim_candidates.md"


def main() -> int:
    records = load_jsonl(DATASET_PATH)
    report = build_outcome_state_report(records)
    OUT_JSON_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD_PATH.write_text(render_outcome_state_markdown(report), encoding="utf-8")
    print(f"Wrote {OUT_JSON_PATH}")
    print(f"Wrote {OUT_MD_PATH}")
    print(
        "Outcome-state report: "
        f"{report['summary']['records_with_risky_actions']} records with risky actions, "
        f"{report['summary']['outcome_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
