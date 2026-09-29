"""Deterministic backend for tests and offline demos (no network)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .base import Decision, ScoreDecision


class MockBackend:
    """Returns scripted answers keyed by input text; records every call."""

    def __init__(self, answers: Mapping[str, tuple[Any, float]] | None = None) -> None:
        self.answers = dict(answers or {})
        self.calls: list[str] = []

    def choose(self, text: str, choices: Mapping[str, str], instructions: str = "") -> Decision:
        self.calls.append(text)
        choice, conf = self.answers.get(text, (next(iter(choices)), 0.0))
        return Decision(choice=choice, confidence=conf)

    def score(self, text: str, levels: Sequence[str], instructions: str = "") -> ScoreDecision:
        self.calls.append(text)
        idx, conf = self.answers.get(text, (0, 0.0))
        return ScoreDecision(int(idx), float(idx), conf)
