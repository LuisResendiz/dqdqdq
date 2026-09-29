"""pandas integration for FuzzyModel.parse_frame."""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any

from .backends import Backend

if TYPE_CHECKING:
    import pandas as pd

    from .model import FuzzyModel


def parse_frame(
    model: type[FuzzyModel],
    df: pd.DataFrame,
    column: str | None,
    columns: Sequence[str] | None,
    backend: Backend | None,
    threshold: float,
) -> pd.DataFrame:
    if (column is None) == (columns is None):
        raise ValueError("Pass exactly one of column= or columns=")
    if column is not None:
        rows: list[Any] = df[column].fillna("").astype(str).tolist()
    else:
        assert columns is not None
        sub = df[list(columns)].fillna("").astype(str)
        rows = sub.to_dict(orient="records")
    results = model.parse_many(rows, backend, threshold)
    out = df.copy()
    names = list(results[0].fields) if results else []
    for n in names:
        out[n] = [_plain(r.fields[n].value) for r in results]
        out[f"{n}_confidence"] = [r.fields[n].confidence for r in results]
    out["needs_review"] = [r.needs_review for r in results]
    return out


def _plain(v: Any) -> Any:
    return v.value if isinstance(v, Enum) else v
