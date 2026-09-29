import pandas as pd

from dqdqdq import ChoiceField, MockBackend, classify, classify_frame, clean_countries
from dqdqdq.cli import main


def test_clean_countries_dedupes_backend_calls() -> None:
    b = MockBackend({"Wakanda": ("KE", 0.3)})
    df = pd.DataFrame({"c": ["Mexico", "Wakanda", "Wakanda", None], "x": [1, 2, 3, 4]})
    out = clean_countries(df, "c", b)
    assert list(out.alpha_3[:3]) == ["MEX", "KEN", "KEN"]
    assert list(out.needs_review) == [False, True, True, True]
    assert b.calls == ["Wakanda"]
    assert list(out.x) == [1, 2, 3, 4]


SEV = ChoiceField({"low": "minor", "high": "outage"}, "severity?")


def test_classify_exact_backend_and_none() -> None:
    b = MockBackend({"site down": ("high", 0.97)})
    assert classify("LOW", SEV, b).source == "exact"
    m = classify("site down", SEV, b)
    assert (m.value, m.source, m.needs_review) == ("high", "backend", False)
    assert classify("site down", SEV).needs_review


def test_classify_frame() -> None:
    b = MockBackend({"boom": ("high", 0.5)})
    df = pd.DataFrame({"t": ["low", "boom"]})
    out = classify_frame(df, "t", SEV, "severity", b)
    assert list(out.severity) == ["low", "high"]
    assert list(out.severity_needs_review) == [False, True]


def test_cli_local_only(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    src = tmp_path / "in.csv"
    src.write_text("id,country\n1,Alemania\n2,Untied States\n")
    dst = tmp_path / "out.csv"
    assert main(["countries", str(src), "-c", "country", "-o", str(dst), "--no-jev"]) == 0
    out = pd.read_csv(dst)
    assert list(out.alpha_3) == ["DEU", "USA"]
    assert "0 need review" in capsys.readouterr().err
