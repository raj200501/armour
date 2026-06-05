# Contributing

Armour is early. Contributions are most useful when they improve the benchmark,
trace adapters, policy replay, or reproducibility.

## Useful Contributions

- New eval cases with clear policy boundaries.
- Sanitized representative traces for coding, browser, MCP, or workflow agents.
- Trace adapters for exported agent logs.
- Monitor improvements with tests and before/after examples.
- Reviewer-workflow improvements that make labels easier to audit.
- Documentation that clarifies methodology, limitations, or reproduction.

Please keep private strategy notes, target lists, personal contact plans, and
non-technical campaign material out of the public repo.

## Development Checks

Run these before opening a PR or committing a public artifact:

```bash
python3 -m compileall -q armour_labs scripts tests
python3 -m unittest discover -s tests
python3 scripts/check_no_secrets.py
```

If you change benchmark generation logic, also regenerate the affected artifact:

```bash
python3 scripts/generate_model_claim_judge_comparison.py
python3 scripts/generate_outcome_state_report.py
```

## Eval Case Guidelines

Good eval cases have:

- a specific user request
- allowed tools and forbidden tools
- concrete safe behavior
- concrete risky behavior
- a trace-level reason why final-answer-only grading would miss something

Avoid vague "be safe" tasks. The best cases make the boundary auditable from
the tool trace.

## Data Guidelines

- Use synthetic or explicitly shareable traces.
- Remove real names, emails, account IDs, secrets, tokens, URLs, and customer
  data.
- Prefer small fixtures that can be inspected in a code review.
- Include both safe and risky examples when adding a new class of behavior.
