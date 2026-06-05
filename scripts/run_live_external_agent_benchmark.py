"""Collect live traces from the tiny external MCP agent."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.dataset import write_jsonl
from armour_labs.live_external import collect_live_external_records


AGENT_SCRIPT = ROOT / "examples" / "external_agents" / "tiny_mcp_agent.py"
DATASET_PATH = ROOT / "datasets" / "live_external_agent_runs.jsonl"


def main() -> int:
    records = collect_live_external_records(AGENT_SCRIPT)
    write_jsonl(records, DATASET_PATH)
    print(f"Wrote {len(records)} live external traces to {DATASET_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
