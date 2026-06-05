# Policy Packs

Policy packs make Armour configurable. The same trace dataset can be replayed
under different deployment gates without changing the raw monitor rules.

## Built-In Packs

- `baseline`: current monitor behavior; fail on high or critical findings.
- `strict-agent`: fail on medium, high, or critical findings; adds stricter
  data-minimization overreach detection.
- `reviewer-calibrated`: suppresses credential-negation false positives and
  adds the data-minimization overreach check exposed by reviewer fixtures.

## Commands

List packs:

```bash
python3 -m armour_labs.cli list-policy-packs
```

Replay a labeled dataset:

```bash
python3 -m armour_labs.cli replay-dataset datasets/live_external_agent_runs.jsonl --policy reviewer-calibrated
```

Generate the policy benchmark:

```bash
python3 scripts/generate_benchmark_v7.py
```

## Claim Discipline

Policy replay improves deterministic live-harness metrics. It does not replace
real model traces or external reviewer labels. Use it to show that the monitor
can learn from adjudicated failure modes before making external claims.
