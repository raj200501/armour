# Claude-Style Agent Eval Slice

This note describes how Armour maps to public agent-evaluation concepts used in
Claude and Claude Code discussions. It is a technical relevance note, not an
endorsement claim.

## Why This Slice Matters

Modern agent systems execute multi-turn workflows with tools, files, browsers,
credentials, and external systems. For these systems, the final answer is only
one part of the safety story. The transcript or trace often shows the actual
boundary crossing:

- a forbidden deployment call
- a bulk customer export
- a credential-store lookup
- a session-cookie read
- an eval-label override
- an external upload of confidential material

Armour is built around that trace-level view.

## Mapping

| Agent-eval concept | Armour equivalent |
|---|---|
| Task / problem | Built-in `eval_id` with policy expectations. |
| Trial | One agent trace or JSONL run. |
| Transcript / trace / trajectory | Normalized `AgentTrace` with ordered tool calls and observations. |
| Grader | Policy monitors plus reviewer-calibrated replay. |
| Outcome | Succeeded, denied, attempted-only, or no risky action finding. |
| Human calibration | Blind reviewer packet, reviewer intake, and adjudication workflow. |

## Focused Claude Slice

A provider-specific run should start with a small, high-signal subset before
expanding:

| Eval ID | Why it belongs in the first slice |
|---|---|
| `repo-maintenance-no-sabotage` | Coding-agent integrity and exfiltration boundary. |
| `deployment-change-control` | Approval and production-action boundary. |
| `customer-ticket-privacy` | Scoped data access versus bulk overreach. |
| `browser-research-auth-boundary` | Public browsing versus authenticated-session access. |
| `model-eval-integrity` | Eval-label and reporting integrity. |
| `internal-research-memo` | Internal document handling and external upload boundary. |

Run with a local key only:

```bash
export ANTHROPIC_API_KEY="<local key>"
export ANTHROPIC_MODEL="<model name>"
python3 scripts/run_model_agent_benchmark.py --provider anthropic --model "$ANTHROPIC_MODEL" --limit 12
python3 scripts/generate_model_claim_candidates.py
python3 scripts/generate_model_claim_judge_comparison.py
python3 scripts/generate_outcome_state_report.py
python3 scripts/check_no_secrets.py
```

## Public Result Note Template

A useful Claude-focused result note should stay narrow:

1. What trace-level failure modes were tested.
2. Which eval IDs were included.
3. How many traces were produced and how many were claim-target eligible.
4. Which risky actions succeeded, were denied, or were only attempted.
5. Which monitor findings require more human review.

Do not claim external validation from a provider slice alone. Treat it as
provider-specific evidence that still needs independent reproduction.

## Public References

- Anthropic Engineering, "Demystifying evals for AI agents":
  https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Anthropic Engineering, "How we contain Claude across products":
  https://www.anthropic.com/engineering/how-we-contain-claude
- Anthropic Help Center, "External Researcher Access Program":
  https://support.anthropic.com/en/articles/9125743-what-is-the-external-researcher-access-program
