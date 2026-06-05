# Judge Baselines

Benchmark v3 compares Armour rule monitors against an offline rubric judge.

The offline judge is intentionally not called an LLM result:

- it uses deterministic rubric patterns
- it makes no network calls
- it costs nothing to run
- it exposes the interface needed to replace it with a real model judge later

Use it to test benchmark plumbing and disagreement workflows. Do not cite it as
frontier-model judge evidence.

## Current Baseline

- Module: `armour_labs/judge_baseline.py`
- Report: `benchmarks/armour_agent_safety_v3.md`
- Disagreement queue: `datasets/adjudication_queue_v3.jsonl`

## Next Step

Replace the offline rubric with a real LLM-as-judge adapter once API budget or a
local model is available. Keep the same output shape so Benchmark v3 and later
reports remain comparable.

## Model Judge Adapter

Benchmark v4 adds `armour_labs/model_judge.py` and
`scripts/run_model_judge_baseline.py`. The adapter returns the same
`predicted_risky`, `confidence`, and `rationale` fields expected by the
benchmark workflow, but reads credentials only from environment variables.

Dry-run command:

```bash
python3 scripts/run_model_judge_baseline.py datasets/live_external_agent_runs.jsonl --dry-run --provider gemini --model dry-run-gemini
```

Real model-judge outputs should be treated as reviewer assistance, not ground
truth. Keep human adjudication for benchmark claims.

## Claim-Candidate Comparison

Benchmark v13 adds `armour_labs/judge_comparison.py` and
`scripts/generate_model_claim_judge_comparison.py` for the real model-backed
claim-candidate set. The current report is
`benchmarks/model_claim_judge_comparison.md`.

The default comparison is still conservative: Armour is compared with an
offline generic judge proxy unless
`benchmarks/model_judge_predictions_claim_candidates.json` exists. That makes
the artifact useful for showing failure-mode coverage without overstating it
as live frontier-model judge evidence.
