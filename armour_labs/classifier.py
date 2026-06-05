"""A tiny dependency-free text classifier for risky agent traces."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{1,}")


class TextSafetyClassifier:
    """Multinomial naive Bayes over trace text.

    This is deliberately simple. It gives the project a trainable baseline that
    can run without API keys or third-party packages, then be replaced by a
    stronger model once labels and budget exist.
    """

    def __init__(self) -> None:
        self.labels: list[str] = []
        self.label_counts: Counter[str] = Counter()
        self.token_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.vocabulary: set[str] = set()

    def fit(self, examples: Iterable[tuple[str, str]]) -> "TextSafetyClassifier":
        for text, label in examples:
            self.labels.append(label)
            self.label_counts[label] += 1
            tokens = _tokenize(text)
            self.token_counts[label].update(tokens)
            self.vocabulary.update(tokens)
        if not self.label_counts:
            raise ValueError("At least one labeled example is required.")
        self.labels = sorted(self.label_counts)
        return self

    def predict(self, text: str) -> str:
        scores = self.predict_log_scores(text)
        return max(scores, key=scores.get)

    def predict_log_scores(self, text: str) -> dict[str, float]:
        if not self.label_counts:
            raise ValueError("Classifier has not been trained.")
        tokens = _tokenize(text)
        total_examples = sum(self.label_counts.values())
        vocab_size = max(1, len(self.vocabulary))
        scores: dict[str, float] = {}
        for label in self.labels:
            prior = math.log(self.label_counts[label] / total_examples)
            token_total = sum(self.token_counts[label].values())
            score = prior
            for token in tokens:
                count = self.token_counts[label][token]
                score += math.log((count + 1) / (token_total + vocab_size))
            scores[label] = score
        return scores

    def save(self, path: str | Path) -> None:
        payload = {
            "labels": self.labels,
            "label_counts": dict(self.label_counts),
            "token_counts": {label: dict(counts) for label, counts in self.token_counts.items()},
            "vocabulary": sorted(self.vocabulary),
        }
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "TextSafetyClassifier":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        model = cls()
        model.labels = list(payload["labels"])
        model.label_counts = Counter(payload["label_counts"])
        model.token_counts = defaultdict(Counter)
        for label, counts in payload["token_counts"].items():
            model.token_counts[label] = Counter(counts)
        model.vocabulary = set(payload["vocabulary"])
        return model


def train_from_reports(reports: Iterable[dict[str, Any]]) -> TextSafetyClassifier:
    examples: list[tuple[str, str]] = []
    for report in reports:
        for result in report.get("results", []):
            label = "risky" if result.get("verdict") == "fail" else "safe"
            trace = result.get("trace", {})
            examples.append((_trace_payload_to_text(trace), label))
    if not examples:
        raise ValueError("No report results found to train on.")
    return TextSafetyClassifier().fit(examples)


def classify_report(report: dict[str, Any], model: TextSafetyClassifier) -> list[dict[str, str]]:
    predictions: list[dict[str, str]] = []
    for result in report.get("results", []):
        trace = result.get("trace", {})
        text = _trace_payload_to_text(trace)
        predictions.append(
            {
                "eval_id": str(result.get("eval_id", trace.get("eval_id", ""))),
                "agent_id": str(result.get("agent_id", trace.get("agent_id", ""))),
                "prediction": model.predict(text),
            }
        )
    return predictions


def _trace_payload_to_text(trace: dict[str, Any]) -> str:
    parts: list[str] = [str(trace.get("eval_id", "")), str(trace.get("agent_id", ""))]
    for action in trace.get("actions", []):
        parts.extend(
            [
                str(action.get("tool", "")),
                str(action.get("input", "")),
                str(action.get("observation", "")),
            ]
        )
        metadata = action.get("metadata", {})
        if isinstance(metadata, dict):
            parts.extend(f"{key}={value}" for key, value in metadata.items())
    parts.append(str(trace.get("final_answer", "")))
    return "\n".join(parts)


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]
