"""The backend contract: given text and a set of choices, pick one with a confidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Decision:
    choice: str
    confidence: float
    probabilities: Mapping[str, float] | None = None


class Backend(Protocol):
    def choose(
        self, text: str, choices: Mapping[str, str], instructions: str = ""
    ) -> Decision:
        """Pick one key of ``choices`` (key -> human description) for ``text``."""
        ...
