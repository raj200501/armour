# Model-Backed Runs

Benchmark v4 adds the first real-call path for Armour. The current run path
supports Gemini, Anthropic, and OpenAI-compatible chat APIs without third-party
dependencies.

## Secret Rules

- Never commit API keys.
- Never put a real key in README files, benchmark reports, datasets, shell
  history examples, or git-tracked `.env` files.
- Prefer process environment variables such as `GEMINI_API_KEY`,
  `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`.
- Run `python3 scripts/check_no_secrets.py` before committing.
- If a key appears in a screenshot, chat, or terminal transcript, rotate it.

`.env` and `.env.*` are ignored by git. They can be used locally, but the
scripts do not require them.

## Gemini Run

```bash
export GEMINI_API_KEY="<local key, never commit>"
export GEMINI_MODEL="gemini-flash-latest"
python3 scripts/run_model_agent_benchmark.py --provider gemini --model "$GEMINI_MODEL" --limit 10
python3 scripts/generate_model_claim_candidates.py
python3 -m armour_labs.cli trace-manifest datasets/model_agent_claim_candidates.jsonl --policy reviewer-calibrated --out benchmarks/trace_evidence_manifest_model_claim_candidates.json
python3 scripts/generate_benchmark_v4.py
python3 scripts/check_no_secrets.py
```

The Gemini client sends the key as an HTTP header, not as a query string.

## Anthropic Run

```bash
export ANTHROPIC_API_KEY="<local key, never commit>"
export ANTHROPIC_MODEL="<anthropic model name>"
python3 scripts/run_model_agent_benchmark.py --provider anthropic --model "$ANTHROPIC_MODEL" --limit 20
python3 scripts/run_model_judge_baseline.py datasets/model_agent_runs.jsonl --provider anthropic --model "$ANTHROPIC_MODEL"
python3 scripts/generate_model_claim_judge_comparison.py
python3 -m armour_labs.cli external-gate-status datasets/model_agent_runs.jsonl --out review/external_gate_status_model.json
python3 scripts/check_no_secrets.py
```

The Anthropic client sends the key as an `x-api-key` HTTP header and uses the
Messages API response text blocks for JSON parsing.

## OpenAI-Compatible Run

```bash
export OPENAI_API_KEY="<local key, never commit>"
export OPENAI_MODEL="<model name>"
python3 scripts/run_model_agent_benchmark.py --provider openai-compatible --model "$OPENAI_MODEL" --limit 20
python3 scripts/run_model_judge_baseline.py datasets/model_agent_runs.jsonl --provider openai-compatible --model "$OPENAI_MODEL"
python3 scripts/generate_model_claim_judge_comparison.py
python3 scripts/generate_benchmark_v4.py
python3 scripts/check_no_secrets.py
```

For a non-OpenAI compatible endpoint, also set `OPENAI_BASE_URL` or pass
`--base-url`.

## Dry Run

CI uses dry-run mode so the repo can verify the workflow without spending API
credits:

```bash
python3 scripts/run_model_agent_benchmark.py --dry-run --provider gemini --model dry-run-gemini --limit 2
python3 scripts/run_model_agent_benchmark.py --dry-run --provider anthropic --model dry-run-claude --limit 2
python3 scripts/run_model_judge_baseline.py datasets/live_external_agent_runs.jsonl --dry-run --provider gemini --model dry-run-gemini
python3 scripts/generate_benchmark_v4.py
```

Dry-run artifacts record planned eval IDs, providers, and output paths. They do
not record credentials or make network calls.

## Output Files

- `datasets/model_agent_runs.jsonl`: model-generated MCP-style trace records
  from the real-call agent collector.
- `datasets/model_agent_claim_candidates.jsonl`: replay-clean model-backed
  records suitable for reviewer packets and gate-status counting.
- `benchmarks/model_claim_candidate_replay.json`: summary of records excluded
  from the claim-candidate set by policy replay.
- `benchmarks/trace_evidence_manifest_model_claim_candidates.json`:
  conservative gate manifest for replay-clean model-backed records.
- `benchmarks/model_judge_predictions.json`: model judge predictions for a
  labeled dataset.
- `benchmarks/model_judge_predictions_claim_candidates.json`: optional live
  model judge predictions for claim-candidate comparison.
- `benchmarks/model_claim_judge_comparison.json`: reviewer-calibrated monitor
  comparison against a generic judge proxy or optional live model judge.
- `benchmarks/outcome_state_model_claim_candidates.json`: attempted, denied,
  and succeeded risky-action outcomes for model-backed claim candidates.
- `benchmarks/armour_agent_safety_v4.md`: Benchmark v4 report.
- `benchmarks/armour_agent_safety_v4_summary.json`: machine-readable v4
  summary.

Model-generated traces still need independent human review before they can be
used as external validation. The model-backed record gate can be clear while the
external-review gate remains blocked.
