"""Deterministic backend for tests and offline demos (no network)."""

from __future__ import annotations

from collections.abc import Mapping

from .base import Decision


class MockBackend:
    """Returns scripted answers keyed by input text; records every call."""

    def __init__(self, answers: Mapping[str, tuple[str, float]] | None = None) -> None:
        self.answers = dict(answers or {})
        self.calls: list[str] = []

    def choose(self, text: str, choices: Mapping[str, str], instructions: str = "") -> Decision:
        self.calls.append(text)
        choice, conf = self.answers.get(text, (next(iter(choices)), 0.0))
        return Decision(choice=choice, confidence=conf)
