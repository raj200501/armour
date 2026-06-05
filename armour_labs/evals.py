"""Eval loading utilities."""

from __future__ import annotations

import json
from pathlib import Path

from armour_labs.eval_catalog import generate_catalog
from armour_labs.schemas import EvalCase


DATA_PATH = Path(__file__).with_name("data") / "evals.json"


def load_seed_evals() -> list[EvalCase]:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [EvalCase.from_dict(item) for item in payload]


def load_builtin_evals() -> list[EvalCase]:
    return generate_catalog(load_seed_evals())


def get_eval(eval_id: str) -> EvalCase:
    for eval_case in load_builtin_evals():
        if eval_case.id == eval_id:
            return eval_case
    raise KeyError(f"Unknown eval id: {eval_id}")


def filter_evals(eval_ids: list[str] | None = None) -> list[EvalCase]:
    evals = load_builtin_evals()
    if not eval_ids:
        return evals
    wanted = set(eval_ids)
    selected = [eval_case for eval_case in evals if eval_case.id in wanted]
    missing = sorted(wanted - {eval_case.id for eval_case in selected})
    if missing:
        raise KeyError(f"Unknown eval id(s): {', '.join(missing)}")
    return selected
