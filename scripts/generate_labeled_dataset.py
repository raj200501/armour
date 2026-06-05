"""Generate the local-agent labeled trace dataset."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.dataset import build_local_agent_dataset, write_jsonl


DATASET_PATH = ROOT / "datasets" / "local_agent_labeled_traces.jsonl"


def main() -> int:
    records = build_local_agent_dataset()
    write_jsonl(records, DATASET_PATH)
    print(f"Wrote {len(records)} labeled traces to {DATASET_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
