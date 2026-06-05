"""Shared data structures for evals, traces, findings, and reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    """A synthetic scenario used to evaluate a tool-using agent."""

    id: str
    title: str
    prompt: str
    allowed_tools: list[str]
    forbidden_tools: list[str]
    red_flags: list[str]
    success_criteria: list[str]
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvalCase":
        return cls(
            id=str(payload["id"]),
            title=str(payload["title"]),
            prompt=str(payload["prompt"]),
            allowed_tools=list(payload.get("allowed_tools", [])),
            forbidden_tools=list(payload.get("forbidden_tools", [])),
            red_flags=list(payload.get("red_flags", [])),
            success_criteria=list(payload.get("success_criteria", [])),
            tags=list(payload.get("tags", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentAction:
    """One tool call, reasoning step, or externally visible agent action."""

    step: int
    tool: str
    input: str
    observation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentAction":
        return cls(
            step=int(payload.get("step", 0)),
            tool=str(payload.get("tool", "")),
            input=str(payload.get("input", "")),
            observation=str(payload.get("observation", "")),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def searchable_text(self) -> str:
        metadata_text = " ".join(f"{key}={value}" for key, value in self.metadata.items())
        return f"{self.tool}\n{self.input}\n{self.observation}\n{metadata_text}".strip()


@dataclass(frozen=True)
class AgentTrace:
    """Actions produced by an agent while attempting an eval case."""

    eval_id: str
    agent_id: str
    actions: list[AgentAction]
    final_answer: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentTrace":
        return cls(
            eval_id=str(payload["eval_id"]),
            agent_id=str(payload.get("agent_id", "unknown")),
            actions=[AgentAction.from_dict(item) for item in payload.get("actions", [])],
            final_answer=str(payload.get("final_answer", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "eval_id": self.eval_id,
            "agent_id": self.agent_id,
            "actions": [action.to_dict() for action in self.actions],
            "final_answer": self.final_answer,
        }

    def searchable_text(self) -> str:
        actions = "\n\n".join(action.searchable_text() for action in self.actions)
        return f"{actions}\n\nfinal_answer={self.final_answer}".strip()


@dataclass(frozen=True)
class MonitorFinding:
    """A monitor alert tied to a specific action in a trace."""

    eval_id: str
    action_step: int
    rule_id: str
    severity: str
    message: str
    evidence: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvalResult:
    """Safety result for one eval case."""

    eval_id: str
    title: str
    agent_id: str
    verdict: str
    risk_level: str
    score: int
    findings: list[MonitorFinding]
    trace: AgentTrace

    def to_dict(self) -> dict[str, Any]:
        return {
            "eval_id": self.eval_id,
            "title": self.title,
            "agent_id": self.agent_id,
            "verdict": self.verdict,
            "risk_level": self.risk_level,
            "score": self.score,
            "findings": [finding.to_dict() for finding in self.findings],
            "trace": self.trace.to_dict(),
        }
