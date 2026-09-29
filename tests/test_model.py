from enum import Enum
from typing import Annotated, Literal

import pandas as pd

from okayish import Fuzzy, FuzzyModel, MockBackend
from okayish.contrib.countries import Country
from okayish.contrib.seniority import Seniority


class Dept(str, Enum):
    billing = "billing"
    technical = "technical"


class Ticket(FuzzyModel):
    severity: Annotated[Literal["low", "medium", "high"], Fuzzy("severity?", threshold=0.9)]
    department: Annotated[Dept, Fuzzy("team?", descriptions={"billing": "payments"})]
    is_outage: Annotated[bool, Fuzzy("Is this an outage?")]
    note: str = ""


def backend() -> MockBackend:
    return MockBackend(
        {
            ("site down", "severity?"): ("high", 0.97),
            ("site down", "team?"): ("technical", 0.99),
            ("site down", "Is this an outage?"): (0.95, 0.0),
            ("meh", "severity?"): ("medium", 0.6),
            ("meh", "team?"): ("billing", 0.9),
            ("meh", "Is this an outage?"): (0.1, 0.0),
        }
    )


def test_parse_typed_values_and_confidence() -> None:
    r = Ticket.parse("site down", backend(), note="x")
    assert r.severity.value == "high" and r.severity.confidence == 0.97
    assert r.value is not None and r.value.department is Dept.technical
    assert r.value.is_outage is True and r.value.note == "x"
    assert not r.needs_review


def test_per_field_threshold_flags_review() -> None:
    r = Ticket.parse("meh", backend())
    assert r.severity.needs_review  # 0.6 < 0.9
    assert not r.is_outage.needs_review and r.needs_review


def test_exact_label_skips_backend() -> None:
    b = MockBackend()
    r = Ticket.parse("LOW", b)
    assert r.severity.value == "low" and r.severity.source == "exact"


def test_no_backend_flags_and_value_none() -> None:
    r = Ticket.parse("site down")
    assert r.needs_review and r.value is None and r.department.source == "none"


def test_parse_many_dedupes() -> None:
    b = backend()
    res = Ticket.parse_many(["site down", "site down", "meh"], b)
    assert len(res) == 3 and res[0] is res[1]
    assert b.calls.count("site down") == 3  # 3 fields, once


class Expense(FuzzyModel):
    matches: Annotated[bool, Fuzzy("same purchase?", source="tx")]


def test_mapping_input_and_source_key() -> None:
    b = MockBackend({("SQ *BLUE BOTTLE", "same purchase?"): (0.9, 0.0)})
    r = Expense.parse({"tx": "SQ *BLUE BOTTLE", "receipt": "Blue Bottle Coffee"}, b)
    assert r.matches.value is True and abs(r.matches.confidence - 0.9) < 1e-9


def test_parse_frame() -> None:
    df = pd.DataFrame({"text": ["site down", "meh"], "id": [1, 2]})
    out = Ticket.parse_frame(df, column="text", backend=backend())
    assert list(out.severity) == ["high", "medium"]
    assert list(out.department) == ["technical", "billing"]
    assert list(out.needs_review) == [False, True] and list(out.id) == [1, 2]


class Person(FuzzyModel):
    level: Seniority


def test_seniority_resolver_uses_score() -> None:
    b = MockBackend()
    r = Person.parse({"title": "Sr. Data Wrangler", "duties": "leads 5 people"}, b)
    assert r.level.source == "backend" and r.level.value == "intern"  # mock default idx 0
    key = "title: Sr. Data Wrangler\nduties: leads 5 people"
    b2 = MockBackend({key: (3, 0.9)})
    r2 = Person.parse({"title": "Sr. Data Wrangler", "duties": "leads 5 people"}, b2)
    assert r2.level.value == "senior" and not r2.needs_review


class Trip(FuzzyModel):
    country: Country


def test_country_plugin() -> None:
    r = Trip.parse("Alemania")
    assert r.value is not None and r.value.country == "DE"
    assert r.country.detail.alpha_3 == "DEU" and not r.needs_review
