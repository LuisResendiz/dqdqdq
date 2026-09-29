"""pandas helpers: add resolved columns next to a messy one."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .backends import Backend
from .choices import ChoiceField, classify
from .countries import resolve_countries

if TYPE_CHECKING:
    import pandas as pd


def clean_countries(
    df: pd.DataFrame,
    column: str,
    backend: Backend | None = None,
    threshold: float = 0.85,
) -> pd.DataFrame:
    """Return a copy of ``df`` with alpha_2, alpha_3, country_name, confidence, source, needs_review."""
    import pandas as pd

    res = resolve_countries(df[column].fillna("").astype(str), backend, threshold)
    out = pd.DataFrame(
        {
            "alpha_2": [r.alpha_2 for r in res],
            "alpha_3": [r.alpha_3 for r in res],
            "country_name": [r.name for r in res],
            "confidence": [r.confidence for r in res],
            "source": [r.source for r in res],
            "needs_review": [r.needs_review for r in res],
        },
        index=df.index,
    )
    return pd.concat([df, out], axis=1)


def classify_frame(
    df: pd.DataFrame,
    column: str,
    spec: ChoiceField,
    name: str,
    backend: Backend | None = None,
    threshold: float = 0.85,
) -> pd.DataFrame:
    """Return a copy of ``df`` with ``{name}``, ``{name}_confidence`` and ``{name}_needs_review``."""
    cache: dict[str, tuple[str | None, float, bool]] = {}
    for v in df[column].fillna("").astype(str).unique():
        m = classify(v, spec, backend, threshold)
        cache[v] = (m.value, m.confidence, m.needs_review)
    keys = df[column].fillna("").astype(str)
    out = df.copy()
    out[name] = [cache[k][0] for k in keys]
    out[f"{name}_confidence"] = [cache[k][1] for k in keys]
    out[f"{name}_needs_review"] = [cache[k][2] for k in keys]
    return out
