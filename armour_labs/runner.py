"""Suite execution and report creation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from armour_labs.evals import filter_evals, get_eval
from armour_labs.monitors import analyze_trace
from armour_labs.policy_packs import (
    apply_policy_pack,
    get_policy_pack,
    policy_risk_level,
    policy_score,
    policy_verdict,
)
from armour_labs.schemas import AgentTrace, EvalResult
from armour_labs.simulator import simulate_agent


def run_suite(profile: str, eval_ids: list[str] | None = None, policy_id: str | None = None) -> dict[str, Any]:
    policy = get_policy_pack(policy_id)
    results: list[EvalResult] = []
    for eval_case in filter_evals(eval_ids):
        trace = simulate_agent(eval_case, profile)
        findings = analyze_trace(eval_case, trace)
        findings = apply_policy_pack(eval_case, trace, findings, policy)
        results.append(
            EvalResult(
                eval_id=eval_case.id,
                title=eval_case.title,
                agent_id=trace.agent_id,
                verdict=policy_verdict(findings, policy),
                risk_level=policy_risk_level(findings),
                score=policy_score(findings),
                findings=findings,
                trace=trace,
            )
        )
    return _report(profile, results, policy_id=policy.id)


def scan_trace(trace: AgentTrace, policy_id: str | None = None) -> dict[str, Any]:
    policy = get_policy_pack(policy_id)
    eval_case = get_eval(trace.eval_id)
    findings = analyze_trace(eval_case, trace)
    findings = apply_policy_pack(eval_case, trace, findings, policy)
    result = EvalResult(
        eval_id=eval_case.id,
        title=eval_case.title,
        agent_id=trace.agent_id,
        verdict=policy_verdict(findings, policy),
        risk_level=policy_risk_level(findings),
        score=policy_score(findings),
        findings=findings,
        trace=trace,
    )
    return _report(trace.agent_id, [result], policy_id=policy.id)


def load_trace(path: str | Path) -> AgentTrace:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "trace" in payload and isinstance(payload["trace"], dict):
        payload = payload["trace"]
    return AgentTrace.from_dict(payload)


def write_report(report: dict[str, Any], out_path: str | Path) -> None:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _report(agent_profile: str, results: list[EvalResult], policy_id: str = "baseline") -> dict[str, Any]:
    fail_count = sum(1 for result in results if result.verdict == "fail")
    critical_count = sum(
        1 for result in results for finding in result.findings if finding.severity == "critical"
    )
    high_count = sum(1 for result in results for finding in result.findings if finding.severity == "high")
    average_score = round(sum(result.score for result in results) / len(results), 2) if results else 0
    return {
        "suite": "armour-agent-safety-v0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agent_profile": agent_profile,
        "policy_pack": policy_id,
        "summary": {
            "eval_count": len(results),
            "pass_count": len(results) - fail_count,
            "fail_count": fail_count,
            "critical_findings": critical_count,
            "high_findings": high_count,
            "average_score": average_score,
        },
        "results": [result.to_dict() for result in results],
    }
