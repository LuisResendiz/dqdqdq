"""Job title + responsibilities -> seniority level (uses the backend's ordered ``score``)."""

from __future__ import annotations

from typing import Annotated, Literal

from ..backends import Backend
from ..model import FieldResult, Fuzzy

LEVELS = ["intern", "junior", "mid", "senior", "lead", "director", "executive"]
_RUBRIC = [
    "Intern or trainee: learning, closely supervised",
    "Junior: executes well-defined tasks with guidance",
    "Mid-level: works independently on typical problems",
    "Senior: owns complex work, mentors others, sets technical direction",
    "Lead or manager: leads a team or a major area, accountable for outcomes",
    "Director: leads multiple teams or a function, shapes strategy",
    "Executive: company-wide accountability (VP, C-level)",
]


def seniority_resolver(
    text: str, backend: Backend | None, threshold: float, instructions: str
) -> FieldResult:
    if backend is None:
        return FieldResult(None, 0.0, "none", True)
    d = backend.score(
        text,
        _RUBRIC,
        instructions
        or "What seniority level does this job have? Judge by responsibilities more than the "
        "title, since titles are inconsistent across companies.",
    )
    return FieldResult(LEVELS[d.score], d.confidence, "backend", d.confidence < threshold, d)


Seniority = Annotated[
    Literal["intern", "junior", "mid", "senior", "lead", "director", "executive"],
    Fuzzy(resolver=seniority_resolver),
]
