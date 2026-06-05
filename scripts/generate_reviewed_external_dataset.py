"""Generate reviewed external-style trace fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.dataset import write_jsonl
from armour_labs.reviewed_fixtures import build_reviewed_external_dataset


DATASET_PATH = ROOT / "datasets" / "reviewed_external_agent_traces.jsonl"


def main() -> int:
    records = build_reviewed_external_dataset()
    write_jsonl(records, DATASET_PATH)
    print(f"Wrote {len(records)} reviewed traces to {DATASET_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
