"""Resolve messy country strings to ISO 3166-1 alpha-2 / alpha-3 codes.

Strategy, cheapest first:
1. exact match on a normalized index (codes, English names, translated names, aliases)
2. fuzzy match (rapidfuzz) if clearly better than the runner-up
3. optional decision-model backend (Jev) choosing among all ~249 countries
Anything still below ``threshold`` is flagged ``needs_review``.
"""

from __future__ import annotations

import gettext
import os
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated, Literal

import pycountry
from rapidfuzz import fuzz, process

from ..backends import Backend
from ..model import FieldResult, Fuzzy
from ..text import normalize

if TYPE_CHECKING:
    import pandas as pd

Source = Literal["exact", "fuzzy", "backend", "none"]

# Common informal names / abbreviations that ISO data does not carry.
ALIASES: dict[str, str] = {
    "usa": "US", "u s a": "US", "u s": "US", "us": "US", "america": "US",
    "united states of america": "US", "estados unidos": "US", "eeuu": "US", "ee uu": "US",
    "uk": "GB", "u k": "GB", "great britain": "GB", "england": "GB", "scotland": "GB",
    "wales": "GB", "reino unido": "GB", "britain": "GB",
    "uae": "AE", "emiratos arabes unidos": "AE",
    "holland": "NL", "the netherlands": "NL", "russia": "RU", "south korea": "KR",
    "north korea": "KP", "korea": "KR", "vietnam": "VN", "czech republic": "CZ",
    "czechia": "CZ", "ivory coast": "CI", "burma": "MM", "turkey": "TR", "turkiye": "TR",
    "mexico": "MX", "mejico": "MX", "deutschland": "DE", "espana": "ES",
}


@dataclass(frozen=True)
class CountryMatch:
    input: str
    alpha_2: str | None
    alpha_3: str | None
    name: str | None
    confidence: float
    source: Source
    needs_review: bool


@lru_cache(maxsize=1)
def _index() -> dict[str, str]:
    """normalized name -> alpha_2. Earlier inserts win on collisions."""
    idx: dict[str, str] = {}

    def add(name: str | None, code: str) -> None:
        if name:
            idx.setdefault(normalize(name), code)

    for c in pycountry.countries:
        add(c.alpha_2, c.alpha_2)
        add(c.alpha_3, c.alpha_2)
        for attr in ("name", "official_name", "common_name"):
            add(getattr(c, attr, None), c.alpha_2)
    for alias, code in ALIASES.items():
        idx[normalize(alias)] = code
    for lang in sorted(os.listdir(pycountry.LOCALES_DIR)):
        try:
            tr = gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=[lang])
        except OSError:
            continue
        for c in pycountry.countries:
            add(tr.gettext(c.name), c.alpha_2)
    return idx


@lru_cache(maxsize=1)
def _keys() -> list[str]:
    return [k for k in _index() if len(k) > 3]  # skip codes for fuzzy matching


def _build(text: str, code: str | None, conf: float, source: Source, threshold: float) -> CountryMatch:
    c = pycountry.countries.get(alpha_2=code) if code else None
    return CountryMatch(
        input=text,
        alpha_2=c.alpha_2 if c else None,
        alpha_3=c.alpha_3 if c else None,
        name=c.name if c else None,
        confidence=conf if c else 0.0,
        source=source if c else "none",
        needs_review=(not c) or conf < threshold,
    )


def resolve_country(
    text: str,
    backend: Backend | None = None,
    threshold: float = 0.85,
    fuzzy_cutoff: float = 88.0,
) -> CountryMatch:
    norm = normalize(text or "")
    if not norm:
        return _build(text, None, 0.0, "none", threshold)
    idx = _index()
    if norm in idx:
        return _build(text, idx[norm], 1.0, "exact", threshold)

    hits = process.extract(norm, _keys(), scorer=fuzz.WRatio, limit=5)
    if hits:
        best_key, best_score, _ = hits[0]
        best_code = idx[best_key]
        rival = next((s for k, s, _ in hits[1:] if idx[k] != best_code), 0.0)
        if best_score >= fuzzy_cutoff and best_score - rival >= 3:
            return _build(text, best_code, best_score / 100 * 0.95, "fuzzy", threshold)

    if backend is not None:
        choices = {c.alpha_2: c.name for c in pycountry.countries}
        d = backend.choose(
            text, choices, "Which country does this text refer to? It may be misspelled or "
            "written in any language."
        )
        return _build(text, d.choice, d.confidence, "backend", threshold)
    return _build(text, None, 0.0, "none", threshold)


def resolve_countries(
    values: Iterable[str],
    backend: Backend | None = None,
    threshold: float = 0.85,
    max_workers: int = 8,
) -> list[CountryMatch]:
    """Batch version: each distinct value is resolved once, backend calls run concurrently."""
    values = list(values)
    unique = list(dict.fromkeys(values))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        done = dict(zip(unique, pool.map(lambda v: resolve_country(v, backend, threshold), unique)))
    return [done[v] for v in values]


def country_resolver(
    text: str, backend: Backend | None, threshold: float, instructions: str
) -> FieldResult:
    m = resolve_country(text, backend, threshold)
    return FieldResult(m.alpha_2, m.confidence, m.source, m.needs_review, detail=m)


Country = Annotated[str, Fuzzy(resolver=country_resolver)]
"""Field type for a ``FuzzyModel``: value is the ISO alpha-2 code, ``detail`` the CountryMatch."""


def clean_countries(
    df: pd.DataFrame, column: str, backend: Backend | None = None, threshold: float = 0.85
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
