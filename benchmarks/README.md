# Benchmarks

This directory contains public benchmark artifacts for Armour's trace-level
agent safety workflow.

## Current Artifacts

| Artifact | Purpose |
|---|---|
| `model_claim_judge_comparison.md` | Compares the reviewer-calibrated Armour monitor with a generic offline LLM-judge-style proxy. |
| `model_claim_judge_comparison.json` | Machine-readable version of the judge-comparison report. |
| `outcome_state_model_claim_candidates.md` | Separates risky action intent from execution outcome. |
| `outcome_state_model_claim_candidates.json` | Machine-readable outcome-state report. |

## Current Metrics

| Metric | Armour monitor | Generic proxy |
|---|---:|---:|
| Accuracy | 1.00 | 0.75 |
| Recall | 1.00 | 0.50 |
| F1 | 1.00 | 0.67 |
| False negatives | 0 | 5 |

## Limitations

- The generic judge baseline is an offline proxy unless live model-judge
  predictions are supplied.
- Current model traces are a compact claim-target set, not a broad population
  study.
- Anonymous or operator-attested review evidence is useful for iteration but
  weaker than named/public independent reproduction.
