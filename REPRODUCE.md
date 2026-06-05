# Reproduce Armour

This guide rebuilds the public technical artifacts from a fresh checkout.

## Setup

```bash
git clone https://github.com/raj200501/armour.git
cd armour
python3 -m unittest discover -s tests
```

No network or API key is required for the default tests and offline benchmark
artifacts.

## Rebuild Live External-Harness Traces

```bash
python3 scripts/run_live_external_agent_benchmark.py
python3 scripts/generate_benchmark_v3.py
```

Expected shape:

- 32 live external-harness traces
- 16 safe labels
- 16 risky labels
- at least one expected false positive and one expected false negative in the
  intentionally simple monitor/judge comparison

## Rebuild Model Claim Candidates

```bash
python3 scripts/generate_model_claim_candidates.py
```

This uses the checked-in model trace dataset and writes the claim-target
dataset under `datasets/`.

## Rebuild Judge Comparison

```bash
python3 scripts/generate_model_claim_judge_comparison.py
```

Expected current output:

- 20 claim-target records
- Armour reviewer-calibrated monitor accuracy: 1.0
- Generic offline LLM-judge-style proxy accuracy: 0.75
- Generic proxy false negatives: 5

## Rebuild Outcome-State Report

```bash
python3 scripts/generate_outcome_state_report.py
```

Expected current output:

- 21 records
- 15 risky action findings
- 10 succeeded risky action findings
- 3 denied risky action findings
- 2 attempted-only risky action findings

## Optional Real Model Runs

Real model calls are optional and require local environment variables. Do not
commit keys.

```bash
export GEMINI_API_KEY="<local key>"
export GEMINI_MODEL="gemini-flash-latest"
python3 scripts/run_model_agent_benchmark.py --provider gemini --model "$GEMINI_MODEL" --limit 10
python3 scripts/generate_model_claim_candidates.py
```

Supported providers:

- `gemini`
- `anthropic`
- `openai-compatible`

## Verification

```bash
python3 -m compileall -q armour_labs scripts tests
python3 -m unittest discover -s tests
python3 scripts/check_no_secrets.py
```
