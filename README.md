# Armour

Armour is a dependency-light evaluation framework for **trace-level safety in
tool-using AI agents**.

Most agent evaluations inspect the final answer. Armour inspects the action
trace: which tools were called, with what arguments, under what policy, and
whether the agent accurately reported what happened.

![Judge comparison](docs/assets/judge-comparison.svg)

## Why Trace-Level Evaluation

As agents move from chat to action, many important failures happen before the
final response:

- forbidden tool calls
- credential access
- data overreach
- audit tampering
- false completion
- unsafe autonomy
- retention-policy violations
- external exfiltration

Armour turns those failures into reviewable trace records, policy checks,
benchmark reports, and reproducible artifacts.

## What Is Included

| Component | Status |
|---|---|
| Eval catalog | 100 safety cases across software, customer data, finance, HR, procurement, browser, retention, eval integrity, and internal-data workflows |
| Trace schema | Normalized JSON/JSONL event format for tool calls, tool results, final answers, labels, reviews, and provenance |
| Monitors | Rule-based detectors for tool misuse, data overreach, credential access, false completion, policy bypass, and audit tampering |
| Replay | Policy-pack replay over recorded trace datasets |
| Model runs | Optional Gemini, Anthropic, and OpenAI-compatible JSON clients using local environment variables only |
| Review workflow | Blind trace-review packet generation, reviewer intake validation, and adjudication utilities |
| Benchmarks | Judge comparison and outcome-state reports over model-backed claim-target traces |

## Benchmark Slices

Armour is designed to support multiple trace-level agent safety slices:

- SaaS authorization and scope-boundary testing
- credential and secret handling
- data overreach and cross-tenant access
- audit-log and evidence tampering
- false completion and unsupported claims
- external exfiltration
- unsafe autonomous escalation

## Results Snapshot

Current public artifacts:

- 100 built-in eval cases
- 32 external-agent harness traces
- 22 model-backed trace records
- 20 model-backed claim-target traces
- calibrated trace-replay policy
- judge-comparison report
- outcome-state report

On the current 20-record claim-target calibration set, the reviewer-calibrated
Armour monitor produced no observed classification errors, while the generic
offline LLM-judge-style proxy missed five risky tool-use traces. The detailed
report includes the sample-size caveats; the front-page result is the error
pattern.

| Baseline | Records | TP | FP | TN | FN | Main Readout |
|---|---:|---:|---:|---:|---:|---|
| Armour reviewer-calibrated monitor | 20 | 10 | 0 | 10 | 0 | 0 observed monitor errors |
| Generic LLM-judge-style proxy | 20 | 5 | 0 | 10 | 5 | Missed 5 / 10 risky traces |

See:

- [Benchmark card](docs/BENCHMARK_CARD.md)
- [Representative traces](docs/REPRESENTATIVE_TRACES.md)
- [Judge comparison](benchmarks/model_claim_judge_comparison.md)
- [Outcome-state report](benchmarks/outcome_state_model_claim_candidates.md)
- [Claude-style agent eval slice](docs/CLAUDE_AGENT_EVALS.md)
- [Reproducibility guide](REPRODUCE.md)

![Outcome-state breakdown](docs/assets/outcome-state.svg)

## Architecture

```mermaid
flowchart LR
    A["Agent trace"] --> B["Trace adapter"]
    B --> C["Normalized events"]
    C --> D["Policy monitors"]
    C --> E["Reviewer packet"]
    D --> F["Safety report"]
    E --> G["Adjudication"]
    G --> H["Reviewer-calibrated replay"]
    H --> I["Benchmark artifacts"]
```

## Quickstart

Requires Python 3.10+.

```bash
git clone https://github.com/raj200501/armour.git
cd armour

python3 -m armour_labs.cli list-evals
python3 -m armour_labs.cli scan-log examples/agent_logs/mcp_customer_ticket.jsonl \
  --format mcp-jsonl \
  --eval-id customer-ticket-privacy \
  --agent-id example-mcp-agent
```

Optional editable install:

```bash
python3 -m pip install -e .
armour list-evals
```

## Reproduce The Main Artifacts

```bash
python3 scripts/run_live_external_agent_benchmark.py
python3 scripts/generate_model_claim_candidates.py
python3 scripts/generate_model_claim_judge_comparison.py
python3 scripts/generate_outcome_state_report.py
```

## Full Verification

The full local verification suite is intentionally lower in the README because
it runs the subprocess-backed external-agent tests.

```bash
python3 -m compileall -q armour_labs scripts tests
python3 -m unittest discover -s tests
python3 scripts/check_no_secrets.py
```

For optional real model calls, set provider keys in the local process
environment. Never commit API keys or put them in command arguments.

```bash
export GEMINI_API_KEY="<local key>"
export GEMINI_MODEL="gemini-flash-latest"
python3 scripts/run_model_agent_benchmark.py --provider gemini --model "$GEMINI_MODEL" --limit 10
```

## Project Layout

```text
armour_labs/      Core library: schemas, monitors, adapters, replay, review, model clients
benchmarks/       Public benchmark outputs and result summaries
datasets/         Example and generated trace datasets
docs/             Technical documentation
examples/         Tiny external-agent harness and sample traces
review/           Reviewer adjudication artifacts used by benchmark comparison
scripts/          Reproducible generation scripts
tests/            Unit tests
```

## Public Artifact Docs

- [Benchmark card](docs/BENCHMARK_CARD.md)
- [Representative traces](docs/REPRESENTATIVE_TRACES.md)
- [Claude-style agent eval slice](docs/CLAUDE_AGENT_EVALS.md)
- [Security policy](SECURITY.md)
- [Contributing guide](CONTRIBUTING.md)

## Claim Discipline

Armour is an early evaluation framework, not a finished safety product.

The current reports support narrow technical claims about this repo's trace
schema, monitor behavior, benchmark workflow, and current datasets. Stronger
external claims require broader providers, more real traces, named/public
reviewer evidence, and independent reproduction.

## License

MIT.
