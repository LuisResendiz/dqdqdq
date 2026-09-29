"""The backend contract: given text and a set of choices, pick one with a confidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Decision:
    choice: str
    confidence: float
    probabilities: Mapping[str, float] | None = None


@dataclass(frozen=True)
class ScoreDecision:
    score: int  # index into the ordered levels (0 = lowest)
    expected: float  # probability-weighted score, smoother than ``score``
    confidence: float
    probabilities: Mapping[int, float] | None = None


class Backend(Protocol):
    def choose(
        self, text: str, choices: Mapping[str, str], instructions: str = ""
    ) -> Decision:
        """Pick one key of ``choices`` (key -> human description) for ``text``."""
        ...

    def score(self, text: str, levels: Sequence[str], instructions: str = "") -> ScoreDecision:
        """Rate ``text`` against ordered ``levels`` (lowest first, 2-10 levels)."""
        ...

    def probability(self, text: str, statement: str) -> float:
        """Probability (0-1) that ``statement`` is true of ``text``."""
        ...
