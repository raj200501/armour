# Safety Case

Armour Labs is designed for defensive evaluation of tool-using AI agents.

## Threat Model

The initial suite targets failures that are plausible for increasingly capable
agents:

- sabotage of tests, logs, labels, or audit trails
- false completion or dishonest self-reporting
- private data exposure
- credential access or requests
- crossing authentication or privilege boundaries
- unauthorized financial or production actions
- bypassing review, rollback, monitoring, or policy gates

## Current Controls

- Evals are synthetic and do not use live systems.
- Risky actions are abstract descriptions, not executable payloads.
- The CLI uses deterministic simulations unless the user supplies a trace.
- Reports preserve evidence snippets so reviewers can reproduce the alert.
- Forbidden tools and scenario-specific red flags are checked per eval.

## Non-Goals

- No exploit development.
- No live target scanning.
- No credential harvesting.
- No production deployment automation.
- No claim that rule-based monitoring is sufficient for frontier deployment.

## Intended Research Use

The MVP should be used to collect traces, compare agents, label failure modes,
and identify monitor gaps. The long-term goal is a benchmark and monitoring
stack that can be independently validated by safety researchers and agent
platform teams.
