"""Deterministic backend for tests and offline demos (no network)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .base import Decision, ScoreDecision


class MockBackend:
    """Returns scripted answers keyed by input text; records every call."""

    def __init__(self, answers: Mapping[Any, tuple[Any, float]] | None = None) -> None:
        self.answers = dict(answers or {})
        self.calls: list[str] = []

    def _answer(self, text: str, instructions: str, default: tuple[Any, float]) -> tuple[Any, float]:
        # a (text, instructions) key targets one field; a bare text key answers any field
        hit = self.answers.get((text, instructions), self.answers.get(text, default))
        return hit  # type: ignore[no-any-return]

    def choose(self, text: str, choices: Mapping[str, str], instructions: str = "") -> Decision:
        self.calls.append(text)
        choice, conf = self._answer(text, instructions, (next(iter(choices)), 0.0))
        return Decision(choice=choice, confidence=conf)

    def score(self, text: str, levels: Sequence[str], instructions: str = "") -> ScoreDecision:
        self.calls.append(text)
        idx, conf = self._answer(text, instructions, (0, 0.0))
        return ScoreDecision(int(idx), float(idx), conf)

    def probability(self, text: str, statement: str) -> float:
        self.calls.append(text)
        p, _ = self._answer(text, statement, (0.5, 0.0))
        return float(p)
