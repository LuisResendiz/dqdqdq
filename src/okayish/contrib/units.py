"""Normalize units of measure ("pcs", "piezas", "Kilos", "5 lbs") to canonical units.

No extra dependencies. Local alias table first; the backend (if given) chooses among the
canonical units for anything else. A leading quantity ("5 pcs") is parsed into ``detail``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Annotated, Literal

from ..backends import Backend
from ..model import FieldResult, Fuzzy
from ..text import normalize

# canonical unit -> (description, aliases)
UNITS: dict[str, tuple[str, list[str]]] = {
    "piece": ("Individual item or unit count", ["pcs", "pc", "piece", "pieces", "unit", "units", "each", "ea", "unidad", "unidades", "pieza", "piezas", "stk", "stuck", "pz", "u"]),
    "dozen": ("Twelve items", ["dozen", "doz", "docena", "docenas", "dz"]),
    "pack": ("Package or box of items", ["pack", "packs", "pkg", "package", "box", "boxes", "caja", "cajas", "paquete", "paquetes", "carton"]),
    "kg": ("Kilogram, mass", ["kg", "kgs", "kilo", "kilos", "kilogram", "kilograms", "kilogramo", "kilogramos"]),
    "g": ("Gram, mass", ["g", "gr", "gram", "grams", "gramo", "gramos"]),
    "lb": ("Pound, mass", ["lb", "lbs", "pound", "pounds", "libra", "libras"]),
    "oz": ("Ounce, mass", ["oz", "ounce", "ounces", "onza", "onzas"]),
    "t": ("Metric tonne, mass", ["t", "ton", "tons", "tonne", "tonnes", "tonelada", "toneladas"]),
    "l": ("Liter, volume", ["l", "lt", "ltr", "liter", "liters", "litre", "litres", "litro", "litros"]),
    "ml": ("Milliliter, volume", ["ml", "milliliter", "milliliters", "mililitro", "mililitros"]),
    "gal": ("Gallon, volume", ["gal", "gallon", "gallons", "galon", "galones"]),
    "m": ("Meter, length", ["m", "mt", "mts", "meter", "meters", "metre", "metres", "metro", "metros"]),
    "cm": ("Centimeter, length", ["cm", "centimeter", "centimeters", "centimetro", "centimetros"]),
    "mm": ("Millimeter, length", ["mm", "millimeter", "millimeters", "milimetro", "milimetros"]),
    "km": ("Kilometer, length", ["km", "kilometer", "kilometers", "kilometro", "kilometros"]),
    "ft": ("Foot, length", ["ft", "foot", "feet", "pie", "pies"]),
    "in": ("Inch, length", ["in", "inch", "inches", "pulgada", "pulgadas"]),
    "mi": ("Mile, length", ["mi", "mile", "miles", "milla", "millas"]),
    "m2": ("Square meter, area", ["m2", "sqm", "sq m", "square meter", "square meters", "metro cuadrado", "metros cuadrados"]),
    "h": ("Hour, time", ["h", "hr", "hrs", "hour", "hours", "hora", "horas"]),
    "min": ("Minute, time", ["min", "mins", "minute", "minutes", "minuto", "minutos"]),
    "day": ("Day, time", ["day", "days", "d", "dia", "dias"]),
}

_ALIAS = {normalize(a): u for u, (_, aliases) in UNITS.items() for a in aliases}
_QTY = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(.*)$")


@dataclass(frozen=True)
class UnitMatch:
    input: str
    unit: str | None
    quantity: float | None
    confidence: float
    source: str  # "exact" | "backend" | "none"
    needs_review: bool


def normalize_unit(text: str, backend: Backend | None = None, threshold: float = 0.85) -> UnitMatch:
    qty: float | None = None
    body = text or ""
    m = _QTY.match(body)
    if m:
        qty, body = float(m.group(1).replace(",", ".")), m.group(2)
    norm = normalize(body)
    if not norm:
        return UnitMatch(text, None, qty, 0.0, "none", True)
    if norm in _ALIAS:
        return UnitMatch(text, _ALIAS[norm], qty, 1.0, "exact", False)
    if backend is not None:
        d = backend.choose(
            body, {u: desc for u, (desc, _) in UNITS.items()},
            "Which unit of measure does this text refer to? It may be abbreviated, misspelled "
            "or in another language.",
        )
        return UnitMatch(text, d.choice, qty, d.confidence, "backend", d.confidence < threshold)
    return UnitMatch(text, None, qty, 0.0, "none", True)


def unit_resolver(
    text: str, backend: Backend | None, threshold: float, instructions: str
) -> FieldResult:
    m = normalize_unit(text, backend, threshold)
    return FieldResult(m.unit, m.confidence, m.source, m.needs_review, detail=m)


Unit = Annotated[
    Literal[
        "piece", "dozen", "pack", "kg", "g", "lb", "oz", "t", "l", "ml", "gal", "m", "cm", "mm",
        "km", "ft", "in", "mi", "m2", "h", "min", "day",
    ],
    Fuzzy(resolver=unit_resolver),
]
"""Field type for a ``FuzzyModel``: value is the canonical unit, ``detail`` the UnitMatch."""
