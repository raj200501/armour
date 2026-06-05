# Armour Benchmark Card

## Purpose

Armour evaluates whether tool-using agents stay inside policy boundaries while
acting. The benchmark focuses on the action trace, not only the final answer.

The core question is:

> Did the agent call the right tools, with acceptable arguments, under the
> scenario policy, and did it report the outcome honestly?

## Scope

Armour currently covers synthetic and model-backed traces for agent workflows
where safety failures are visible in tool calls:

| Area | Example boundary |
|---|---|
| Software maintenance | Do not sabotage tests, logs, or repository state. |
| Deployment change control | Do not bypass approval, rollback, audit, or monitoring gates. |
| Customer data | Do not expand a scoped ticket investigation into bulk export. |
| Finance | Do not move money or approve payment changes without authority. |
| HR | Do not send confidential candidate content to personal channels. |
| Procurement | Do not request or retrieve vendor credentials. |
| Browser research | Do not cross from public research into authenticated-session access. |
| Retention | Do not delete records before policy clearance. |
| Eval integrity | Do not alter labels, counts, failures, or published eval results. |
| Internal research | Do not move confidential internal documents to public storage. |

## Trace Format

Each record contains:

- an `eval_id`
- an `agent_id`
- ordered tool-call events
- tool results or observations
- a final user-visible report
- a reference or reviewed label

Armour converts raw agent logs into a normalized trace, runs policy monitors,
and preserves evidence snippets for review.

## Grading Philosophy

Armour treats agent safety as an outcome plus trace-review problem:

- A denied forbidden tool call is still safety-relevant because it shows unsafe
  intent or policy confusion.
- A succeeded forbidden tool call is higher impact and should be separated from
  denied or attempted-only actions.
- A truthful final answer can reduce ambiguity, but it does not erase unsafe
  tool use.
- A polished final answer is not enough if the intermediate trace crossed a
  boundary.
- Human review and policy replay are expected; rule monitors are not presented
  as a complete frontier-agent safety solution.

## Public Artifacts

| Artifact | Role |
|---|---|
| `armour_labs/data/evals.json` | Built-in eval catalog. |
| `datasets/model_agent_claim_candidates.jsonl` | Model-backed claim-target traces used in current comparison reports. |
| `review/reviewer_adjudication.json` | Reviewer adjudication artifact for claim-target labels. |
| `benchmarks/model_claim_judge_comparison.md` | Error analysis comparing Armour replay with a generic offline judge proxy. |
| `benchmarks/outcome_state_model_claim_candidates.md` | Separates succeeded, denied, and attempted-only risky actions. |
| `docs/REPRESENTATIVE_TRACES.md` | Short guide to canonical records worth inspecting first. |

## Current Readout

On the current 20-record claim-target set:

| Baseline | Records | False Positives | False Negatives | Risky Traces Missed |
|---|---:|---:|---:|---:|
| Armour reviewer-calibrated monitor | 20 | 0 | 0 | 0 / 10 |
| Generic offline judge proxy | 20 | 0 | 5 | 5 / 10 |

The exact point metrics and small-sample confidence bounds are in
`benchmarks/model_claim_judge_comparison.md`.

## Reproduce

```bash
python3 -m unittest discover -s tests
python3 scripts/generate_model_claim_candidates.py
python3 scripts/generate_model_claim_judge_comparison.py
python3 scripts/generate_outcome_state_report.py
```

Optional provider-backed runs require local environment variables. Never commit
API keys.

```bash
export ANTHROPIC_API_KEY="<local key>"
export ANTHROPIC_MODEL="<model name>"
python3 scripts/run_model_agent_benchmark.py --provider anthropic --model "$ANTHROPIC_MODEL" --limit 20
```

## Limitations

- Current public traces are a compact calibration set, not a broad population
  study.
- Anonymous or operator-attested review evidence is useful for iteration but is
  weaker than named public reproduction.
- The generic judge baseline is an offline rubric proxy unless live model-judge
  predictions are supplied.
- Armour does not claim that rule-based monitors are sufficient for production
  frontier-agent deployment.

## Next Validation Targets

- Run a focused Claude/Anthropic provider slice over the claim-target set.
- Add named/public independent reproduction.
- Add exact adapters for exported coding-agent and browser-agent trace formats.
- Expand beyond synthetic fixtures into more real user-approved agent traces.
