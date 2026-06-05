"""Run model-backed agent trace collection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.dataset import write_jsonl
from armour_labs.evals import filter_evals, load_builtin_evals
from armour_labs.model_agent import MODEL_AGENT_MODES, build_model_client, collect_model_agent_record, dry_run_plan
from armour_labs.model_api import SUPPORTED_PROVIDERS


OUT_PATH = ROOT / "datasets" / "model_agent_runs.jsonl"
DRY_RUN_PATH = ROOT / "datasets" / "model_agent_run_plan.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect model-backed agent traces.")
    parser.add_argument("--provider", choices=SUPPORTED_PROVIDERS, help="Model provider. Defaults to env/autodetect.")
    parser.add_argument("--model", help="Model name. Defaults to provider-specific model env.")
    parser.add_argument("--base-url", help="Provider API base URL override.")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--eval-id", action="append", dest="eval_ids", help="Specific eval id to run. Repeatable.")
    parser.add_argument("--mode", action="append", choices=MODEL_AGENT_MODES, dest="modes")
    parser.add_argument("--out", default=str(OUT_PATH))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    eval_cases = filter_evals(args.eval_ids) if args.eval_ids else load_builtin_evals()[: args.limit]
    eval_ids = [eval_case.id for eval_case in eval_cases]
    modes = args.modes or list(MODEL_AGENT_MODES)
    if args.dry_run:
        DRY_RUN_PATH.write_text(
            json.dumps(dry_run_plan(eval_ids, modes, args.provider, args.model), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote dry-run plan to {DRY_RUN_PATH}")
        return 0

    client = build_model_client(provider=args.provider, model=args.model, base_url=args.base_url)
    records = [collect_model_agent_record(eval_id, mode, client) for eval_id in eval_ids for mode in modes]
    write_jsonl(records, args.out)
    print(f"Wrote {len(records)} model-backed traces to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
