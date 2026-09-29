from typing import Annotated

import pytest

from okayish import Fuzzy, FuzzyModel, MockBackend
from okayish.contrib.currencies import Currency, resolve_currency
from okayish.contrib.units import Unit, normalize_unit


@pytest.mark.parametrize(
    "text,code",
    [("US dollars", "USD"), ("Euro", "EUR"), ("€", "EUR"), ("pesos mx", "MXN"),
     ("Dólar estadounidense", "USD"), ("mxn", "MXN"), ("Swiss Frank", "CHF"), ("yen", "JPY")],
)
def test_currency_local(text: str, code: str) -> None:
    m = resolve_currency(text)
    assert m.code == code and not m.needs_review, m


def test_ambiguous_symbol_is_flagged() -> None:
    m = resolve_currency("$")
    assert m.code == "USD" and m.needs_review


def test_currency_backend_fallback_and_unknown() -> None:
    b = MockBackend({"moneda de la reina": ("GBP", 0.9)})
    assert resolve_currency("moneda de la reina", b).code == "GBP"
    assert resolve_currency("zzzz").needs_review


@pytest.mark.parametrize(
    "text,unit,qty",
    [("pcs", "piece", None), ("Piezas", "piece", None), ("5 kilos", "kg", 5.0),
     ("2,5 lbs", "lb", 2.5), ("Litros", "l", None), ("docena", "dozen", None)],
)
def test_units_local(text: str, unit: str, qty: float | None) -> None:
    m = normalize_unit(text)
    assert (m.unit, m.quantity) == (unit, qty) and not m.needs_review


def test_units_backend_and_unknown() -> None:
    assert normalize_unit("bananas").needs_review
    b = MockBackend({"kilogramz": ("kg", 0.95)})
    assert normalize_unit("kilogramz", b).unit == "kg"


class Line(FuzzyModel):
    currency: Annotated[Currency, Fuzzy(source="cur")]
    unit: Annotated[Unit, Fuzzy(source="u")]


def test_in_fuzzymodel_with_mapping_input() -> None:
    r = Line.parse({"cur": "pesos mx", "u": "5 piezas", "price": "10"})
    assert r.value is not None and (r.value.currency, r.value.unit) == ("MXN", "piece")
    assert r.unit.detail.quantity == 5.0 and not r.needs_review
