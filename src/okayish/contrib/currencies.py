"""Resolve messy currency text ("US dollars", "$", "pesos mx", "Euro") to ISO 4217 codes.

Same strategy as countries: exact index (codes, names, translations, aliases), then fuzzy
matching, then an optional backend choosing among all ISO currencies. Ambiguous symbols
like "$" resolve to a best guess with reduced confidence so they get reviewed.
"""

from __future__ import annotations

import gettext
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Literal

import pycountry
from rapidfuzz import fuzz, process

from ..backends import Backend
from ..model import FieldResult, Fuzzy
from ..text import normalize

Source = Literal["exact", "fuzzy", "backend", "none"]

ALIASES: dict[str, str] = {
    "us dollar": "USD", "us dollars": "USD", "dolar": "USD", "dolares": "USD", "usd": "USD",
    "euro": "EUR", "euros": "EUR", "eur": "EUR", "pound sterling": "GBP", "sterling": "GBP",
    "pounds": "GBP", "gbp": "GBP", "yen": "JPY", "yuan": "CNY", "rmb": "CNY", "renminbi": "CNY",
    "pesos mexicanos": "MXN", "peso mexicano": "MXN", "pesos mx": "MXN", "mxn": "MXN",
    "mx pesos": "MXN", "reais": "BRL", "real": "BRL", "rupees": "INR", "rupee": "INR",
    "swiss franc": "CHF", "francos suizos": "CHF", "canadian dollars": "CAD", "cad": "CAD",
    "australian dollars": "AUD", "aud": "AUD", "won": "KRW", "ruble": "RUB", "rubles": "RUB",
}
# symbol -> (code, confidence): the symbol alone is genuinely ambiguous
SYMBOLS: dict[str, tuple[str, float]] = {
    "€": ("EUR", 0.99), "£": ("GBP", 0.9), "$": ("USD", 0.6), "us$": ("USD", 0.97),
    "¥": ("JPY", 0.55), "₹": ("INR", 0.99), "₩": ("KRW", 0.98), "₽": ("RUB", 0.99),
    "r$": ("BRL", 0.97), "mx$": ("MXN", 0.97), "c$": ("CAD", 0.9), "a$": ("AUD", 0.9),
    "chf": ("CHF", 1.0), "₺": ("TRY", 0.99), "₪": ("ILS", 0.99), "₫": ("VND", 0.99),
}


@dataclass(frozen=True)
class CurrencyMatch:
    input: str
    code: str | None
    name: str | None
    numeric: str | None
    confidence: float
    source: Source
    needs_review: bool


@lru_cache(maxsize=1)
def _index() -> dict[str, str]:
    idx: dict[str, str] = {}

    def add(name: str | None, code: str) -> None:
        if name:
            idx.setdefault(normalize(name), code)

    for c in pycountry.currencies:
        add(c.alpha_3, c.alpha_3)
        add(c.name, c.alpha_3)
    for alias, code in ALIASES.items():
        idx[normalize(alias)] = code
    for lang in sorted(os.listdir(pycountry.LOCALES_DIR)):
        try:
            tr = gettext.translation("iso4217", pycountry.LOCALES_DIR, languages=[lang])
        except OSError:
            continue
        for c in pycountry.currencies:
            add(tr.gettext(c.name), c.alpha_3)
    return idx


@lru_cache(maxsize=1)
def _keys() -> list[str]:
    return [k for k in _index() if len(k) > 3]


def _build(text: str, code: str | None, conf: float, source: Source, threshold: float) -> CurrencyMatch:
    c = pycountry.currencies.get(alpha_3=code) if code else None
    return CurrencyMatch(
        text,
        c.alpha_3 if c else None,
        c.name if c else None,
        c.numeric if c else None,
        conf if c else 0.0,
        source if c else "none",
        (not c) or conf < threshold,
    )


def resolve_currency(
    text: str, backend: Backend | None = None, threshold: float = 0.85, fuzzy_cutoff: float = 88.0
) -> CurrencyMatch:
    raw = (text or "").strip()
    sym = SYMBOLS.get(raw.casefold())
    if sym:
        return _build(text, sym[0], sym[1], "exact", threshold)
    norm = normalize(raw)
    if not norm:
        return _build(text, None, 0.0, "none", threshold)
    idx = _index()
    if norm in idx:
        return _build(text, idx[norm], 1.0, "exact", threshold)
    hits = process.extract(norm, _keys(), scorer=fuzz.WRatio, limit=5)
    if hits:
        best_key, best_score, _ = hits[0]
        best = idx[best_key]
        rival = next((s for k, s, _ in hits[1:] if idx[k] != best), 0.0)
        if best_score >= fuzzy_cutoff and best_score - rival >= 3:
            return _build(text, best, best_score / 100 * 0.95, "fuzzy", threshold)
    if backend is not None:
        choices = {c.alpha_3: c.name for c in pycountry.currencies}
        d = backend.choose(
            text, choices, "Which currency does this text refer to? It may be a symbol, "
            "a misspelling, or written in any language."
        )
        return _build(text, d.choice, d.confidence, "backend", threshold)
    return _build(text, None, 0.0, "none", threshold)


def currency_resolver(
    text: str, backend: Backend | None, threshold: float, instructions: str
) -> FieldResult:
    m = resolve_currency(text, backend, threshold)
    return FieldResult(m.code, m.confidence, m.source, m.needs_review, detail=m)


Currency = Annotated[str, Fuzzy(resolver=currency_resolver)]
"""Field type for a ``FuzzyModel``: value is the ISO 4217 code, ``detail`` the CurrencyMatch."""
