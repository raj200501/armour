# Trace Evidence Manifest

The trace evidence manifest is a conservative gate for external claims. It is
designed for the point where Armour starts collecting real model-backed traces
and independent reviewer labels.

## Command

```bash
python3 -m armour_labs.cli trace-manifest datasets/live_external_agent_runs.jsonl --policy reviewer-calibrated --adjudication review/reviewer_adjudication.json --out benchmarks/trace_evidence_manifest_live.json
```

## What It Checks

- dataset path, record count, duplicate IDs, required fields, and SHA-256 hash
- label, label-source, agent-family, policy, and review-disposition counts
- model-backed record count and model provider/model counts
- embedded and adjudicated reviewer coverage
- whether reviews are claim-eligible external reviews rather than fixtures
- selected policy-pack replay metrics and replay error count

## Claim Gate

The default gate requires:

- at least 20 model-backed records
- at least 20 claim-eligible externally reviewed records
- at least two reviewers per reviewed record
- no duplicate record IDs or missing required trace fields
- no labeled errors under the selected policy replay

Fixture, operator, local, prompted-reference, synthetic, and internal labels do
not satisfy the external-review gate. They are useful for CI and demos, but not
for public evidence claims.

## Current Status

The current live-harness dataset can pass the policy replay gate under
`reviewer-calibrated`, but it does not pass the external claim gate because it
has zero real model-backed records and zero claim-eligible external reviews.
