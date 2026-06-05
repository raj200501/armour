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

## Current Error Analysis

The current comparison is a compact 20-record claim-target/calibration set. The
point metrics are available in `model_claim_judge_comparison.md`; the safer
public readout is the error pattern:

| Baseline | Records | False Positives | False Negatives | Risky Traces Missed |
|---|---:|---:|---:|---:|
| Armour reviewer-calibrated monitor | 20 | 0 | 0 | 0 / 10 |
| Generic offline judge proxy | 20 | 0 | 5 | 5 / 10 |

## Limitations

- The generic judge baseline is an offline proxy unless live model-judge
  predictions are supplied.
- Current model traces are a compact claim-target set, not a broad population
  study.
- Anonymous or operator-attested review evidence is useful for iteration but
  weaker than named/public independent reproduction.
