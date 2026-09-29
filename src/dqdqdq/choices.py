"""Generic fuzzy classification into a fixed set of labels (severity, department, unit...)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from .backends import Backend
from .countries import normalize


@dataclass(frozen=True)
class ChoiceField:
    """A closed set of labels. ``choices`` maps label -> description shown to the model."""

    choices: Mapping[str, str]
    instructions: str = ""
    aliases: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ChoiceMatch:
    input: str
    value: str | None
    confidence: float
    source: str  # "exact" | "backend" | "none"
    needs_review: bool


def classify(
    text: str, spec: ChoiceField, backend: Backend | None = None, threshold: float = 0.85
) -> ChoiceMatch:
    norm = normalize(text or "")
    if not norm:
        return ChoiceMatch(text, None, 0.0, "none", True)
    lookup = {normalize(k): k for k in spec.choices}
    lookup.update({normalize(a): v for a, v in spec.aliases.items()})
    if norm in lookup:
        return ChoiceMatch(text, lookup[norm], 1.0, "exact", False)
    if backend is None:
        return ChoiceMatch(text, None, 0.0, "none", True)
    d = backend.choose(text, spec.choices, spec.instructions)
    return ChoiceMatch(text, d.choice, d.confidence, "backend", d.confidence < threshold)
