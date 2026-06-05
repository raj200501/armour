"""Adapters from real agent logs into the Armour trace schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from armour_labs.schemas import AgentAction, AgentTrace


SUPPORTED_LOG_FORMATS = ("mcp-jsonl", "mcp-json", "claude-code-jsonl")


def trace_from_agent_log(path: str | Path, log_format: str, eval_id: str, agent_id: str) -> AgentTrace:
    if log_format not in SUPPORTED_LOG_FORMATS:
        raise ValueError(
            f"Unsupported log format '{log_format}'. Expected one of: {', '.join(SUPPORTED_LOG_FORMATS)}"
        )

    events = _load_events(path, log_format)
    return trace_from_agent_events(events, log_format, eval_id, agent_id)


def trace_from_agent_events(
    events: list[dict[str, Any]], log_format: str, eval_id: str, agent_id: str
) -> AgentTrace:
    if log_format not in SUPPORTED_LOG_FORMATS:
        raise ValueError(
            f"Unsupported log format '{log_format}'. Expected one of: {', '.join(SUPPORTED_LOG_FORMATS)}"
        )
    actions, final_answer = _events_to_actions(events, log_format)
    return AgentTrace(eval_id=eval_id, agent_id=agent_id, actions=actions, final_answer=final_answer)


def write_trace(trace: AgentTrace, out_path: str | Path) -> None:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_events(path: str | Path, log_format: str) -> list[dict[str, Any]]:
    source = Path(path)
    if log_format in {"mcp-jsonl", "claude-code-jsonl"}:
        return [
            json.loads(line)
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    payload = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        return [dict(item) for item in payload["events"]]
    raise ValueError("mcp-json expects a JSON list or an object with an 'events' list.")


def _events_to_actions(events: list[dict[str, Any]], log_format: str) -> tuple[list[AgentAction], str]:
    action_payloads: list[dict[str, Any]] = []
    pending_by_call_id: dict[str, dict[str, Any]] = {}
    final_answer = ""

    for index, event in enumerate(events):
        event_type = str(_first_present(event, ("type", "event", "kind")) or "")
        call_id = _call_id(event)

        if _is_final_event(event_type, event):
            final_answer = _stringify(
                _first_present(event, ("final_answer", "message", "content", "text", "output"))
            )
            continue

        if _is_result_event(event_type, event) and call_id in pending_by_call_id:
            pending_by_call_id[call_id]["observation"] = _stringify(
                _first_present(event, ("result", "output", "content", "response", "observation"))
            )
            continue

        tool = _tool_name(event)
        tool_input = _tool_input(event)
        observation = _first_present(event, ("observation", "result", "output", "content", "response"))
        if not tool and tool_input is None and observation is None:
            continue

        payload = {
            "step": len(action_payloads) + 1,
            "tool": tool or "agent_event",
            "input": _stringify(tool_input),
            "observation": _stringify(observation),
            "metadata": {
                "adapter": log_format,
                "event_index": index,
                "event_type": event_type or "unknown",
            },
        }
        if call_id:
            payload["metadata"]["call_id"] = call_id
            pending_by_call_id[call_id] = payload
        action_payloads.append(payload)

    return [AgentAction.from_dict(payload) for payload in action_payloads], final_answer


def _tool_name(event: dict[str, Any]) -> str:
    direct = _first_present(event, ("tool", "tool_name", "name", "server_tool"))
    if direct:
        return str(direct)
    for key in ("tool_call", "toolUse", "tool_use"):
        nested = event.get(key)
        if isinstance(nested, dict):
            nested_name = _first_present(nested, ("tool", "tool_name", "name"))
            if nested_name:
                return str(nested_name)
    return ""


def _tool_input(event: dict[str, Any]) -> Any:
    direct = _first_present(event, ("input", "arguments", "args", "parameters", "tool_input"))
    if direct is not None:
        return direct
    for key in ("tool_call", "toolUse", "tool_use"):
        nested = event.get(key)
        if isinstance(nested, dict):
            nested_input = _first_present(nested, ("input", "arguments", "args", "parameters"))
            if nested_input is not None:
                return nested_input
    return ""


def _call_id(event: dict[str, Any]) -> str:
    direct = _first_present(event, ("call_id", "tool_call_id", "id", "request_id"))
    if direct:
        return str(direct)
    for key in ("tool_call", "toolUse", "tool_use"):
        nested = event.get(key)
        if isinstance(nested, dict):
            nested_id = _first_present(nested, ("call_id", "tool_call_id", "id", "request_id"))
            if nested_id:
                return str(nested_id)
    return ""


def _is_result_event(event_type: str, event: dict[str, Any]) -> bool:
    if event_type.lower() in {"tool_result", "tool-response", "tool_response", "result"}:
        return True
    return "result" in event and not _tool_name(event)


def _is_final_event(event_type: str, event: dict[str, Any]) -> bool:
    if event_type.lower() in {"final", "final_answer", "assistant_final", "completion"}:
        return True
    return "final_answer" in event


def _first_present(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)
