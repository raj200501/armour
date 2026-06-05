"""Command-line interface for Armour Labs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from armour_labs.adapters import SUPPORTED_LOG_FORMATS, trace_from_agent_log, write_trace
from armour_labs.classifier import TextSafetyClassifier, classify_report, train_from_reports
from armour_labs.dataset import load_jsonl
from armour_labs.evals import load_builtin_evals
from armour_labs.external_gate import build_external_gate_status
from armour_labs.metrics import evaluate_labeled_records
from armour_labs.policy_packs import list_policy_packs
from armour_labs.provenance import build_trace_evidence_manifest, load_adjudication
from armour_labs.replay import replay_records
from armour_labs.runner import load_trace, run_suite, scan_trace, write_report
from armour_labs.simulator import PROFILES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="armour", description="Audit tool-using AI agent traces.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-evals", help="List built-in eval cases.")
    list_parser.set_defaults(func=_list_evals)

    policy_parser = subparsers.add_parser("list-policy-packs", help="List built-in policy packs.")
    policy_parser.set_defaults(func=_list_policy_packs)

    run_parser = subparsers.add_parser("run", help="Run built-in evals with a simulated agent profile.")
    run_parser.add_argument("--profile", choices=PROFILES, default="sloppy")
    run_parser.add_argument("--eval-id", action="append", dest="eval_ids", help="Run a specific eval id.")
    run_parser.add_argument("--policy", default="baseline", help="Policy pack id. Defaults to baseline.")
    run_parser.add_argument("--out", help="Write JSON report to this path.")
    run_parser.set_defaults(func=_run)

    scan_parser = subparsers.add_parser("scan-trace", help="Scan an external trace JSON file.")
    scan_parser.add_argument("trace_json", help="Path to AgentTrace JSON.")
    scan_parser.add_argument("--policy", default="baseline", help="Policy pack id. Defaults to baseline.")
    scan_parser.add_argument("--out", help="Write JSON report to this path.")
    scan_parser.set_defaults(func=_scan_trace)

    convert_parser = subparsers.add_parser("convert-log", help="Convert a real agent log to AgentTrace JSON.")
    convert_parser.add_argument("agent_log", help="Path to agent log JSON or JSONL.")
    convert_parser.add_argument("--format", choices=SUPPORTED_LOG_FORMATS, default="mcp-jsonl")
    convert_parser.add_argument("--eval-id", required=True, help="Eval id the log should be scored against.")
    convert_parser.add_argument("--agent-id", required=True, help="Agent or harness identifier.")
    convert_parser.add_argument("--out", required=True, help="Path to write AgentTrace JSON.")
    convert_parser.set_defaults(func=_convert_log)

    scan_log_parser = subparsers.add_parser("scan-log", help="Convert and scan a real agent log.")
    scan_log_parser.add_argument("agent_log", help="Path to agent log JSON or JSONL.")
    scan_log_parser.add_argument("--format", choices=SUPPORTED_LOG_FORMATS, default="mcp-jsonl")
    scan_log_parser.add_argument("--eval-id", required=True, help="Eval id the log should be scored against.")
    scan_log_parser.add_argument("--agent-id", required=True, help="Agent or harness identifier.")
    scan_log_parser.add_argument("--policy", default="baseline", help="Policy pack id. Defaults to baseline.")
    scan_log_parser.add_argument("--out", help="Write JSON report to this path.")
    scan_log_parser.set_defaults(func=_scan_log)

    train_parser = subparsers.add_parser("train", help="Train the tiny text classifier from report JSON files.")
    train_parser.add_argument("reports", nargs="+", help="Report JSON files produced by run or scan-trace.")
    train_parser.add_argument("--model", required=True, help="Path to write the model JSON.")
    train_parser.set_defaults(func=_train)

    classify_parser = subparsers.add_parser("classify", help="Classify traces inside a report JSON file.")
    classify_parser.add_argument("report", help="Report JSON file to classify.")
    classify_parser.add_argument("--model", required=True, help="Path to a trained model JSON.")
    classify_parser.set_defaults(func=_classify)

    eval_labels_parser = subparsers.add_parser("evaluate-labels", help="Evaluate monitor metrics on labeled JSONL.")
    eval_labels_parser.add_argument("dataset_jsonl", help="Labeled dataset JSONL with embedded agent events.")
    eval_labels_parser.add_argument("--out", help="Write metrics JSON to this path.")
    eval_labels_parser.set_defaults(func=_evaluate_labels)

    replay_parser = subparsers.add_parser("replay-dataset", help="Replay a labeled JSONL dataset with a policy pack.")
    replay_parser.add_argument("dataset_jsonl", help="Labeled dataset JSONL with embedded agent events.")
    replay_parser.add_argument("--policy", default="baseline", help="Policy pack id. Defaults to baseline.")
    replay_parser.add_argument("--out", help="Write replay report JSON to this path.")
    replay_parser.set_defaults(func=_replay_dataset)

    manifest_parser = subparsers.add_parser("trace-manifest", help="Build an evidence manifest for a trace dataset.")
    manifest_parser.add_argument("dataset_jsonl", help="Labeled dataset JSONL with embedded agent events.")
    manifest_parser.add_argument("--policy", default="reviewer-calibrated", help="Policy pack id to replay.")
    manifest_parser.add_argument("--adjudication", help="Reviewer adjudication JSON to include.")
    manifest_parser.add_argument("--required-model-records", type=int, default=20)
    manifest_parser.add_argument("--required-reviewed-records", type=int, default=20)
    manifest_parser.add_argument("--minimum-reviewers", type=int, default=2)
    manifest_parser.add_argument("--out", help="Write manifest JSON to this path.")
    manifest_parser.set_defaults(func=_trace_manifest)

    gate_parser = subparsers.add_parser("external-gate-status", help="Report external claim gate blockers.")
    gate_parser.add_argument("dataset_jsonl", help="Labeled dataset JSONL with embedded agent events.")
    gate_parser.add_argument("--policy", default="reviewer-calibrated", help="Policy pack id to replay.")
    gate_parser.add_argument("--adjudication", help="Reviewer adjudication JSON to include.")
    gate_parser.add_argument("--required-model-records", type=int, default=20)
    gate_parser.add_argument("--required-reviewed-records", type=int, default=20)
    gate_parser.add_argument("--minimum-reviewers", type=int, default=2)
    gate_parser.add_argument("--out", help="Write status JSON to this path.")
    gate_parser.set_defaults(func=_external_gate_status)

    args = parser.parse_args(argv)
    return args.func(args)


def _list_evals(_args: argparse.Namespace) -> int:
    for eval_case in load_builtin_evals():
        tags = ",".join(eval_case.tags)
        print(f"{eval_case.id}\t{tags}\t{eval_case.title}")
    return 0


def _list_policy_packs(_args: argparse.Namespace) -> int:
    for policy in list_policy_packs():
        severities = ",".join(policy.fail_severities)
        print(f"{policy.id}\tfail={severities}\t{policy.title}")
    return 0


def _run(args: argparse.Namespace) -> int:
    report = run_suite(profile=args.profile, eval_ids=args.eval_ids, policy_id=args.policy)
    _emit_report(report, args.out)
    summary = report["summary"]
    print(
        f"Ran {summary['eval_count']} evals: "
        f"{summary['pass_count']} pass, {summary['fail_count']} fail, "
        f"avg score {summary['average_score']}."
    )
    return 0


def _scan_trace(args: argparse.Namespace) -> int:
    trace = load_trace(args.trace_json)
    report = scan_trace(trace, policy_id=args.policy)
    _emit_report(report, args.out)
    summary = report["summary"]
    print(
        f"Scanned trace for {trace.eval_id}: "
        f"{summary['pass_count']} pass, {summary['fail_count']} fail."
    )
    return 0


def _convert_log(args: argparse.Namespace) -> int:
    trace = trace_from_agent_log(args.agent_log, args.format, args.eval_id, args.agent_id)
    write_trace(trace, args.out)
    print(f"Wrote {len(trace.actions)} actions to {args.out}.")
    return 0


def _scan_log(args: argparse.Namespace) -> int:
    trace = trace_from_agent_log(args.agent_log, args.format, args.eval_id, args.agent_id)
    report = scan_trace(trace, policy_id=args.policy)
    _emit_report(report, args.out)
    summary = report["summary"]
    print(
        f"Scanned {len(trace.actions)} imported actions for {trace.eval_id}: "
        f"{summary['pass_count']} pass, {summary['fail_count']} fail."
    )
    return 0


def _train(args: argparse.Namespace) -> int:
    reports = [_load_json(path) for path in args.reports]
    model = train_from_reports(reports)
    model.save(args.model)
    print(f"Wrote model to {args.model}.")
    return 0


def _classify(args: argparse.Namespace) -> int:
    report = _load_json(args.report)
    model = TextSafetyClassifier.load(args.model)
    predictions = classify_report(report, model)
    print(json.dumps({"predictions": predictions}, indent=2, sort_keys=True))
    return 0


def _evaluate_labels(args: argparse.Namespace) -> int:
    records = load_jsonl(args.dataset_jsonl)
    metrics = evaluate_labeled_records(records)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metrics["overall"], indent=2, sort_keys=True))
    return 0


def _replay_dataset(args: argparse.Namespace) -> int:
    records = load_jsonl(args.dataset_jsonl)
    report = replay_records(records, policy_id=args.policy)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["overall"], indent=2, sort_keys=True))
    return 0


def _trace_manifest(args: argparse.Namespace) -> int:
    records = load_jsonl(args.dataset_jsonl)
    manifest = build_trace_evidence_manifest(
        records,
        args.dataset_jsonl,
        policy_id=args.policy,
        adjudication=load_adjudication(args.adjudication),
        required_model_backed_records=args.required_model_records,
        required_external_reviewed_records=args.required_reviewed_records,
        minimum_reviewers=args.minimum_reviewers,
    )
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest["claim_status"], indent=2, sort_keys=True))
    return 0


def _external_gate_status(args: argparse.Namespace) -> int:
    records = load_jsonl(args.dataset_jsonl)
    manifest = build_trace_evidence_manifest(
        records,
        args.dataset_jsonl,
        policy_id=args.policy,
        adjudication=load_adjudication(args.adjudication),
        required_model_backed_records=args.required_model_records,
        required_external_reviewed_records=args.required_reviewed_records,
        minimum_reviewers=args.minimum_reviewers,
    )
    status = build_external_gate_status(manifest)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ready_for_external_claim": status["ready_for_external_claim"], "counts": status["counts"]}, indent=2, sort_keys=True))
    return 0


def _emit_report(report: dict[str, Any], out: str | None) -> None:
    if out:
        write_report(report, out)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
