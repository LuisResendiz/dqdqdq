import pytest

from fuzzschema import MockBackend, resolve_country


@pytest.mark.parametrize(
    "text,alpha2,alpha3",
    [
        ("Mexico", "MX", "MEX"), ("México", "MX", "MEX"), ("  usa ", "US", "USA"),
        ("Deutschland", "DE", "DEU"), ("Allemagne", "DE", "DEU"), ("Alemania", "DE", "DEU"),
        ("日本", "JP", "JPN"), ("gb", "GB", "GBR"), ("FRA", "FR", "FRA"),
        ("Untied States", "US", "USA"), ("Germny", "DE", "DEU"), ("Brasill", "BR", "BRA"),
    ],
)
def test_local_resolution(text: str, alpha2: str, alpha3: str) -> None:
    m = resolve_country(text)
    assert (m.alpha_2, m.alpha_3) == (alpha2, alpha3), m
    assert not m.needs_review


def test_unknown_without_backend_is_flagged() -> None:
    m = resolve_country("Wakanda")
    assert m.alpha_2 is None and m.needs_review and m.source == "none"


def test_empty_is_flagged() -> None:
    assert resolve_country("").needs_review


def test_backend_fallback_and_low_confidence() -> None:
    b = MockBackend({"Wakanda": ("KE", 0.4), "la tierra del sol naciente": ("JP", 0.93)})
    low = resolve_country("Wakanda", backend=b)
    assert low.alpha_2 == "KE" and low.source == "backend" and low.needs_review
    hi = resolve_country("la tierra del sol naciente", backend=b)
    assert hi.alpha_3 == "JPN" and not hi.needs_review


def test_backend_not_called_for_easy_values() -> None:
    b = MockBackend()
    resolve_country("Canada", backend=b)
    assert b.calls == []
