"""Pydantic-style fuzzy schemas: declare fields, pass messy text, get typed values + confidence."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, Literal, Protocol, TypeVar, get_args, get_origin

from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo
from typing_extensions import Self

from .backends import Backend
from .text import normalize

if TYPE_CHECKING:
    import pandas as pd

Text = "str | Mapping[str, str]"


@dataclass(frozen=True)
class FieldResult:
    value: Any
    confidence: float
    source: str  # "exact" | "backend" | "fuzzy" | "none" ...
    needs_review: bool
    detail: Any = None  # resolver-specific extras (e.g. a CountryMatch)


class Resolver(Protocol):
    def __call__(
        self, text: str, backend: Backend | None, threshold: float, instructions: str
    ) -> FieldResult: ...


@dataclass(eq=False)  # identity hash: Annotated metadata must be hashable
class Fuzzy:
    """Field metadata: ``severity: Annotated[Literal["low", "high"], Fuzzy("How severe?")]``."""

    instructions: str = ""
    threshold: float | None = None
    source: str | None = None  # which key of a mapping input this field reads
    descriptions: Mapping[str, str] = field(default_factory=dict)  # per-choice hints
    resolver: Resolver | None = None  # custom resolution instead of choose()


def _merge(metadata: Sequence[Any]) -> Fuzzy:
    """Combine every Fuzzy on a field; later ones override, so ``Annotated[Country, Fuzzy(source=..)]`` works."""
    out = Fuzzy()
    for m in metadata:
        if isinstance(m, Fuzzy):
            for f in ("instructions", "threshold", "source", "resolver"):
                if getattr(m, f) not in (None, ""):
                    setattr(out, f, getattr(m, f))
            out.descriptions = {**out.descriptions, **m.descriptions}
    return out


def _choices(annotation: Any, meta: Fuzzy) -> tuple[dict[str, str], Callable[[str], Any]] | None:
    if get_origin(annotation) is Literal:
        vals = [str(v) for v in get_args(annotation)]
        return {v: meta.descriptions.get(v, v) for v in vals}, lambda c: c
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        ch = {str(m.value): meta.descriptions.get(str(m.value), m.name) for m in annotation}
        return ch, lambda c: annotation(c)
    return None


def _resolve(
    info: FieldInfo, meta: Fuzzy, text: str, backend: Backend | None, default: float
) -> FieldResult | None:
    threshold = meta.threshold if meta.threshold is not None else default
    instructions = meta.instructions or info.description or ""
    if meta.resolver is not None:
        return meta.resolver(text, backend, threshold, instructions)
    if info.annotation is bool:
        if backend is None:
            return FieldResult(None, 0.0, "none", True)
        p = backend.probability(text, instructions)
        conf = max(p, 1 - p)  # 0.5 = coin flip, 1.0 = certain either way
        return FieldResult(p >= 0.5, conf, "backend", conf < threshold, detail=p)
    spec = _choices(info.annotation, meta)
    if spec is None:
        return None
    choices, convert = spec
    norm = {normalize(k): k for k in choices}
    hit = norm.get(normalize(text))
    if hit is not None:
        return FieldResult(convert(hit), 1.0, "exact", False)
    if backend is None:
        return FieldResult(None, 0.0, "none", True)
    d = backend.choose(text, choices, instructions)
    return FieldResult(convert(d.choice), d.confidence, "backend", d.confidence < threshold)


def _render(inp: str | Mapping[str, str], source: str | None) -> str:
    if isinstance(inp, str):
        return inp
    if source is not None:
        return str(inp[source])
    return "\n".join(f"{k}: {v}" for k, v in inp.items())


M = TypeVar("M", bound="FuzzyModel")


@dataclass
class ParseResult(Generic[M]):
    fields: dict[str, FieldResult]
    value: M | None  # validated model, or None if a required field could not be resolved

    @property
    def needs_review(self) -> bool:
        return any(f.needs_review for f in self.fields.values())

    def __getattr__(self, name: str) -> FieldResult:
        fields = self.__dict__.get("fields", {})
        if name in fields:
            return fields[name]  # type: ignore[no-any-return]
        raise AttributeError(name)


class FuzzyModel(BaseModel):
    @classmethod
    def parse(
        cls,
        text: str | Mapping[str, str],
        backend: Backend | None = None,
        threshold: float = 0.85,
        **extra: Any,
    ) -> ParseResult[Self]:
        results: dict[str, FieldResult] = {}
        for name, info in cls.model_fields.items():
            meta = _merge(info.metadata)
            r = _resolve(info, meta, _render(text, meta.source), backend, threshold)
            if r is not None:
                results[name] = r
        data = {n: r.value for n, r in results.items() if r.value is not None}
        try:
            value: Self | None = cls.model_validate({**data, **extra})
        except ValidationError:
            value = None
        return ParseResult(results, value)

    @classmethod
    def parse_many(
        cls,
        rows: Sequence[str | Mapping[str, str]],
        backend: Backend | None = None,
        threshold: float = 0.85,
        max_workers: int = 8,
    ) -> list[ParseResult[Self]]:
        """Each distinct input is parsed once; backend calls run concurrently."""
        keys = [json.dumps(r, sort_keys=True) for r in rows]
        unique = dict(zip(keys, rows))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            done = dict(
                zip(unique, pool.map(lambda r: cls.parse(r, backend, threshold), unique.values()))
            )
        return [done[k] for k in keys]

    @classmethod
    def parse_frame(
        cls,
        df: pd.DataFrame,
        column: str | None = None,
        columns: Sequence[str] | None = None,
        backend: Backend | None = None,
        threshold: float = 0.85,
    ) -> pd.DataFrame:
        """Add ``<field>``, ``<field>_confidence`` and ``needs_review`` columns to a copy of ``df``.

        Use ``column`` for one text column, or ``columns`` to pass several as a mapping input.
        """
        from .frame import parse_frame

        return parse_frame(cls, df, column, columns, backend, threshold)
