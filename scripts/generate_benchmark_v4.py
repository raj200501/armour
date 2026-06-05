"""Generate Benchmark v4 for model-backed agent and judge readiness."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from armour_labs.dataset import load_jsonl
from armour_labs.metrics import evaluate_labeled_records
from armour_labs.model_api import SUPPORTED_PROVIDERS


MODEL_AGENT_DATASET_PATH = ROOT / "datasets" / "model_agent_runs.jsonl"
MODEL_AGENT_PLAN_PATH = ROOT / "datasets" / "model_agent_run_plan.json"
MODEL_JUDGE_PLAN_PATH = ROOT / "benchmarks" / "model_judge_plan.json"
MODEL_JUDGE_PREDICTIONS_PATH = ROOT / "benchmarks" / "model_judge_predictions.json"
BENCHMARK_DIR = ROOT / "benchmarks"
REPORT_PATH = BENCHMARK_DIR / "armour_agent_safety_v4.md"
SUMMARY_PATH = BENCHMARK_DIR / "armour_agent_safety_v4_summary.json"


def main() -> int:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    model_records = _load_records_if_present(MODEL_AGENT_DATASET_PATH)
    monitor_metrics = evaluate_labeled_records(model_records)["overall"] if model_records else None
    model_judge_predictions = _load_json_if_present(MODEL_JUDGE_PREDICTIONS_PATH)
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite": "armour-agent-safety-v4",
        "milestone_percent": 50,
        "status": "live-model-traces-present" if model_records else "model-backed-path-ready",
        "provider_support": list(SUPPORTED_PROVIDERS),
        "secret_policy": {
            "credential_env_vars": ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
            "model_env_vars": ["GEMINI_MODEL", "ANTHROPIC_MODEL", "OPENAI_MODEL"],
            "note": "Credentials are intentionally not stored in this artifact.",
            "scanner": "scripts/check_no_secrets.py",
        },
        "model_agent": {
            "dataset_path": "datasets/model_agent_runs.jsonl",
            "records": len(model_records),
            "dry_run_plan_path": "datasets/model_agent_run_plan.json",
            "dry_run_plan": _load_json_if_present(MODEL_AGENT_PLAN_PATH),
        },
        "armour_monitor_metrics": monitor_metrics,
        "model_judge": {
            "predictions_path": "benchmarks/model_judge_predictions.json",
            "prediction_count": _prediction_count(model_judge_predictions),
            "dry_run_plan_path": "benchmarks/model_judge_plan.json",
            "dry_run_plan": _load_json_if_present(MODEL_JUDGE_PLAN_PATH),
        },
        "next_run_commands": [
            'export GEMINI_API_KEY="<local key, never commit>"',
            'export GEMINI_MODEL="<gemini model name>"',
            'python3 scripts/run_model_agent_benchmark.py --provider gemini --model "$GEMINI_MODEL" --limit 20',
            'python3 scripts/run_model_judge_baseline.py datasets/model_agent_runs.jsonl --provider gemini --model "$GEMINI_MODEL"',
            'export ANTHROPIC_API_KEY="<local key, never commit>"',
            'export ANTHROPIC_MODEL="<anthropic model name>"',
            'python3 scripts/run_model_agent_benchmark.py --provider anthropic --model "$ANTHROPIC_MODEL" --limit 20',
            'python3 scripts/run_model_judge_baseline.py datasets/model_agent_runs.jsonl --provider anthropic --model "$ANTHROPIC_MODEL"',
            "python3 scripts/generate_benchmark_v4.py",
            "python3 scripts/check_no_secrets.py",
        ],
        "limitations": [
            "Benchmark v4 readiness artifacts do not prove frontier-model behavior unless model_agent_runs.jsonl is present.",
            "Model-generated labels remain prompted references until independently reviewed.",
            "Real API calls require local environment credentials and network access.",
        ],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(_render_markdown(summary), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    return 0


def _load_records_if_present(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return load_jsonl(path)


def _load_json_if_present(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _prediction_count(payload: dict[str, Any] | None) -> int:
    if not payload:
        return 0
    predictions = payload.get("predictions", [])
    return len(predictions) if isinstance(predictions, list) else 0


def _render_markdown(summary: dict[str, Any]) -> str:
    monitor = summary["armour_monitor_metrics"]
    monitor_table = _monitor_table(monitor)
    commands = "\n".join(f"- `{command}`" for command in summary["next_run_commands"])
    limitations = "\n".join(f"- {item}" for item in summary["limitations"])
    return f"""# Armour Agent Safety Benchmark v4

Generated: {summary["created_at"]}

Benchmark v4 adds the real-call path for a model-backed agent trace collector
and model-backed judge baseline. It supports Gemini, Anthropic, and
OpenAI-compatible APIs through environment variables only. No API key or secret
is stored in this report.

## Status

- Milestone: {summary["milestone_percent"]}%
- Status: `{summary["status"]}`
- Providers: {", ".join(summary["provider_support"])}
- Model-agent records: {summary["model_agent"]["records"]}
- Model-judge predictions: {summary["model_judge"]["prediction_count"]}

## Secret Handling

- Credential env vars: `{", ".join(summary["secret_policy"]["credential_env_vars"])}`
- Model env vars: `{", ".join(summary["secret_policy"]["model_env_vars"])}`
- Scanner: `{summary["secret_policy"]["scanner"]}`
- Policy: {summary["secret_policy"]["note"]}

## Armour Monitor Metrics On Model-Agent Traces

{monitor_table}

## Dry-Run Artifacts

- Model agent plan: `{summary["model_agent"]["dry_run_plan_path"]}`
- Model judge plan: `{summary["model_judge"]["dry_run_plan_path"]}`

## Commands For A Real Local Run

{commands}

## Limitations

{limitations}

## What This Adds

- `armour_labs/model_api.py` implements JSON clients for Gemini, Anthropic, and
  OpenAI-compatible chat APIs without third-party dependencies.
- `armour_labs/model_agent.py` prompts a real model to emit abstract MCP-style
  agent traces for existing Armour evals.
- `armour_labs/model_judge.py` prompts a real model to judge labeled traces
  with the same output shape as the offline judge baseline.
- CI can validate the workflow with dry-run plans and secret scanning without
  spending API credits.
"""


def _monitor_table(metrics: dict[str, Any] | None) -> str:
    if metrics is None:
        return (
            "No model-agent trace dataset is present yet. Run "
            "`scripts/run_model_agent_benchmark.py` with local credentials to "
            "populate `datasets/model_agent_runs.jsonl`."
        )
    return f"""| Records | TP | FP | TN | FN | Precision | Recall | Specificity | Accuracy | F1 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| {metrics["records"]} | {metrics["true_positive"]} | {metrics["false_positive"]} | {metrics["true_negative"]} | {metrics["false_negative"]} | {_pct(metrics["precision"])} | {_pct(metrics["recall"])} | {_pct(metrics["specificity"])} | {_pct(metrics["accuracy"])} | {_pct(metrics["f1"])} |"""


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
