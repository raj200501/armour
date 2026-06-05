"""Generate the first public Armour benchmark report."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.adapters import trace_from_agent_log
from armour_labs.evals import load_builtin_evals
from armour_labs.runner import run_suite, scan_trace


BENCHMARK_DIR = ROOT / "benchmarks"
REPORT_PATH = BENCHMARK_DIR / "armour_agent_safety_v0.md"
SUMMARY_PATH = BENCHMARK_DIR / "armour_agent_safety_v0_summary.json"


def main() -> int:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    profile_reports = {
        "benign": run_suite("benign"),
        "sloppy": run_suite("sloppy"),
        "deceptive": run_suite("deceptive"),
    }
    mcp_trace = trace_from_agent_log(
        ROOT / "examples/agent_logs/mcp_customer_ticket.jsonl",
        "mcp-jsonl",
        "customer-ticket-privacy",
        "example-mcp-agent",
    )
    mcp_report = scan_trace(mcp_trace)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite": "armour-agent-safety-v0",
        "eval_count": len(load_builtin_evals()),
        "profile_reports": {
            profile: report["summary"] for profile, report in profile_reports.items()
        },
        "mcp_adapter_smoke": mcp_report["summary"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(_render_markdown(summary), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    return 0


def _render_markdown(summary: dict[str, Any]) -> str:
    rows = "\n".join(_profile_row(profile, data) for profile, data in summary["profile_reports"].items())
    mcp = summary["mcp_adapter_smoke"]
    catch_rate = _pct(mcp["fail_count"], mcp["eval_count"])
    return f"""# Armour Agent Safety Benchmark v0

Generated: {summary["created_at"]}

This is the first public Armour Labs benchmark artifact. It is a calibration
baseline, not a frontier-model leaderboard. The goal is to prove the full loop:
100 evals, deterministic safe/risky agent profiles, real agent-log import, and
reproducible safety reports.

## Suite

- Eval suite: `{summary["suite"]}`
- Eval cases: {summary["eval_count"]}
- Seed cases: 12 hand-written scenarios
- Generated cases: 88 domain/risk combinations
- Domains: software, browser research, customer support, finance, HR, data
  governance, model evals, security triage, procurement, sales, research
- Risk types: sabotage, data exfiltration, credential access, auth boundary,
  financial overreach, audit tampering, false completion, policy bypass

## Simulated Profile Results

| Profile | Evals | Pass | Fail | Critical Findings | High Findings | Avg Score | Failure Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
{rows}

## Real Agent-Log Adapter Smoke

The benchmark also imports `examples/agent_logs/mcp_customer_ticket.jsonl`, an
MCP-style tool-call log, converts it into the Armour trace schema, and scans it
against `customer-ticket-privacy`.

| Adapter | Imported Actions | Pass | Fail | Critical Findings | High Findings | Catch Rate |
|---|---:|---:|---:|---:|---:|---:|
| `mcp-jsonl` | 2 | {mcp["pass_count"]} | {mcp["fail_count"]} | {mcp["critical_findings"]} | {mcp["high_findings"]} | {catch_rate} |

## Interpretation

- The benign simulated profile has zero monitor failures across the 100-case
  suite.
- The sloppy simulated profile triggers all 100 unsafe scenarios, giving a
  basic monitor coverage check across every generated domain/risk pair.
- The deceptive simulated profile triggers all 100 scenarios through
  false-completion and eval-integrity patterns.
- The MCP adapter smoke test proves Armour can scan a real tool-call log shape,
  not only Armour-native trace JSON.

## Limitations

- Simulated profiles are not frontier-model results.
- The generated eval cases are structured coverage, not human-validated
  benchmark items yet.
- The MCP log is a smoke fixture, not a live production trace.
- Current monitor metrics are detection sanity checks, not precision/recall
  estimates from human-labeled data.

## Next Benchmark

The next report should replace simulated profiles with at least one real agent
harness and add human labels for false positives and false negatives.
"""


def _profile_row(profile: str, summary: dict[str, Any]) -> str:
    return (
        f"| `{profile}` | {summary['eval_count']} | {summary['pass_count']} | "
        f"{summary['fail_count']} | {summary['critical_findings']} | "
        f"{summary['high_findings']} | {summary['average_score']} | "
        f"{_pct(summary['fail_count'], summary['eval_count'])} |"
    )


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
