"""Run model-backed judge baseline on a labeled dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.dataset import load_jsonl
from armour_labs.model_agent import build_model_client
from armour_labs.model_api import SUPPORTED_PROVIDERS
from armour_labs.model_judge import dry_run_plan, judge_record_with_model


OUT_PATH = ROOT / "benchmarks" / "model_judge_predictions.json"
DRY_RUN_PATH = ROOT / "benchmarks" / "model_judge_plan.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run model judge baseline.")
    parser.add_argument("dataset_jsonl")
    parser.add_argument("--provider", choices=SUPPORTED_PROVIDERS, help="Model provider. Defaults to env/autodetect.")
    parser.add_argument("--model", help="Model name. Defaults to provider-specific model env.")
    parser.add_argument("--base-url", help="Provider API base URL override.")
    parser.add_argument("--out", default=str(OUT_PATH))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        DRY_RUN_PATH.write_text(
            json.dumps(dry_run_plan(args.dataset_jsonl, args.provider, args.model), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote dry-run plan to {DRY_RUN_PATH}")
        return 0

    records = load_jsonl(args.dataset_jsonl)
    if args.limit is not None:
        records = records[: args.limit]
    client = build_model_client(provider=args.provider, model=args.model, base_url=args.base_url)
    predictions = [judge_record_with_model(record, client) for record in records]
    output = {"dataset": args.dataset_jsonl, "predictions": predictions}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(predictions)} model judge predictions to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
