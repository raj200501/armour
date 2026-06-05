"""Generate judge comparison for model-backed claim-target traces."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.dataset import load_jsonl
from armour_labs.judge_comparison import (
    build_judge_comparison,
    load_model_predictions,
    render_judge_comparison_markdown,
)
from armour_labs.provenance import load_adjudication


DATASET_PATH = ROOT / "datasets" / "model_agent_claim_candidates.jsonl"
ADJUDICATION_PATH = ROOT / "review" / "reviewer_adjudication.json"
MODEL_PREDICTIONS_PATH = ROOT / "benchmarks" / "model_judge_predictions_claim_candidates.json"
OUT_JSON_PATH = ROOT / "benchmarks" / "model_claim_judge_comparison.json"
OUT_MD_PATH = ROOT / "benchmarks" / "model_claim_judge_comparison.md"


def main() -> int:
    records = load_jsonl(DATASET_PATH)
    adjudication = load_adjudication(ADJUDICATION_PATH)
    model_predictions = load_model_predictions(MODEL_PREDICTIONS_PATH)
    report = build_judge_comparison(records, adjudication, model_predictions=model_predictions)
    OUT_JSON_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD_PATH.write_text(render_judge_comparison_markdown(report), encoding="utf-8")
    print(f"Wrote {OUT_JSON_PATH}")
    print(f"Wrote {OUT_MD_PATH}")
    armour_errors = len(report["armour_error_records"])
    generic_false_negatives = len(report["generic_proxy_missed_risky_records"])
    print(
        "Judge comparison: "
        f"Armour observed errors {armour_errors}/{report['record_count']}, "
        f"generic proxy false negatives {generic_false_negatives}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
