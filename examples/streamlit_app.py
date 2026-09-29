"""Demo UI: uv run --extra app streamlit run examples/streamlit_app.py"""

import os
from enum import Enum
from typing import Annotated, Literal

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from okayish import Fuzzy, FuzzyModel, JevBackend
from okayish.contrib.countries import resolve_country
from okayish.contrib.currencies import resolve_currency
from okayish.contrib.units import normalize_unit

load_dotenv()  # must run before reading the env var below
st.set_page_config(page_title="okayish", page_icon="🧹", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; max-width: 1200px;}
    .hero h1 {font-size: 2.4rem; margin-bottom: .2rem;}
    .hero p {color: #9aa0b4; font-size: 1.05rem; margin-top: 0;}
    .pipe {display:flex; gap:.6rem; margin:.8rem 0 1.4rem; flex-wrap:wrap;}
    .pipe span {background:#1A1D29; border:1px solid #2b2f42; border-radius:999px;
                padding:.3rem .9rem; font-size:.85rem; color:#c9cde0;}
    .pipe b {color:#6C5CE7;}
    div[data-testid="stMetric"] {background:#1A1D29; border:1px solid #2b2f42;
                border-radius:12px; padding:.8rem 1rem;}
    button[data-baseweb="tab"] {font-size:1rem;}
    </style>
    <div class="hero">
      <h1>🧹 okayish</h1>
      <p>Fuzzy data quality: messy values in, typed values with a confidence score out.</p>
    </div>
    <div class="pipe">
      <span><b>1</b> exact match</span><span><b>2</b> fuzzy match</span>
      <span><b>3</b> Jev decision model</span><span><b>4</b> flag for review</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Settings")
    key = st.text_input("Jev API key", type="password", value=os.environ.get("TYPESAFE_API_KEY", ""))
    threshold = st.slider("Review threshold", 0.0, 1.0, 0.85, 0.01,
                          help="Values below this confidence are flagged for review.")
    if key:
        st.success("Jev connected", icon="✅")
    else:
        st.warning("Local only: hard cases stay unresolved", icon="⚠️")
    st.caption("The key stays in this session. Put it in a gitignored `.env` to skip this field.")

SHOWN = ["input", "value", "confidence", "source", "needs_review"]
CONF = st.column_config.ProgressColumn("confidence", min_value=0.0, max_value=1.0, format="%.2f")
FLAG = st.column_config.CheckboxColumn("review?")


def backend() -> JevBackend | None:
    return JevBackend(api_key=key) if key else None


@st.cache_data(show_spinner=False)
def _country(v: str, t: float, k: str) -> dict:
    m = resolve_country(v, JevBackend(api_key=k) if k else None, t)
    return {"input": v, "value": m.alpha_2, "alpha_3": m.alpha_3, "name": m.name,
            "confidence": m.confidence, "source": m.source, "needs_review": m.needs_review}


@st.cache_data(show_spinner=False)
def _currency(v: str, t: float, k: str) -> dict:
    m = resolve_currency(v, JevBackend(api_key=k) if k else None, t)
    return {"input": v, "value": m.code, "name": m.name, "confidence": m.confidence,
            "source": m.source, "needs_review": m.needs_review}


@st.cache_data(show_spinner=False)
def _unit(v: str, t: float, k: str) -> dict:
    m = normalize_unit(v, JevBackend(api_key=k) if k else None, t)
    return {"input": v, "value": m.unit, "quantity": m.quantity, "confidence": m.confidence,
            "source": m.source, "needs_review": m.needs_review}


def show(df: pd.DataFrame) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", len(df))
    c2.metric("Need review", int(df.needs_review.sum()))
    c3.metric("Resolved locally", int(df.source.isin(["exact", "fuzzy"]).sum()))
    c4.metric("Resolved by Jev", int((df.source == "backend").sum()))
    cols = [c for c in df.columns if c in SHOWN or c not in ("input",)]
    cols = ["input"] + [c for c in cols if c != "input"]
    st.dataframe(
        df[cols], hide_index=True, width="stretch",
        column_config={"confidence": CONF, "needs_review": FLAG},
    )
    st.download_button("Download CSV", df.to_csv(index=False), "okayish_clean.csv", "text/csv")


def values_input(name: str, sample: str) -> list[str]:
    left, right = st.columns([3, 2])
    with right:
        up = st.file_uploader("…or upload a CSV", type="csv", key=f"up_{name}")
        col = None
        if up:
            src = pd.read_csv(up)
            col = st.selectbox("Column", src.columns, key=f"col_{name}")
    with left:
        raw = st.text_area("One value per line", sample, height=200, key=f"txt_{name}")
    if up and col:
        return src[col].dropna().astype(str).tolist()
    return [v for v in raw.splitlines() if v.strip()]


tab_c, tab_cur, tab_u, tab_t = st.tabs(["🌍 Countries", "💱 Currencies", "📏 Units", "🎫 Ticket triage"])

with tab_c:
    st.caption("Any language, typos, abbreviations → ISO 3166-1 alpha-2 / alpha-3.")
    vals = values_input("c", "Mexico\nAlemania\nUntied States\nドイツ\nla tierra del sol naciente\nWakanda")
    if st.button("Resolve countries", type="primary", key="b_c"):
        show(pd.DataFrame([_country(v, threshold, key) for v in vals]))

with tab_cur:
    st.caption("Names, symbols and other languages → ISO 4217. Ambiguous symbols like `$` get reviewed.")
    vals = values_input("cur", "US dollars\npesos mx\n$\n€\nDólar estadounidense\nmoneda de la reina")
    if st.button("Resolve currencies", type="primary", key="b_cur"):
        show(pd.DataFrame([_currency(v, threshold, key) for v in vals]))

with tab_u:
    st.caption("Abbreviations and other languages → canonical units. A leading quantity is parsed out.")
    vals = values_input("u", "pcs\n5 piezas\nkilogramz\ndocena\n2,5 lbs\ncajas de 12")
    if st.button("Normalize units", type="primary", key="b_u"):
        show(pd.DataFrame([_unit(v, threshold, key) for v in vals]))


class Department(str, Enum):
    billing = "billing"
    technical = "technical"
    account = "account"


class Ticket(FuzzyModel):
    severity: Annotated[Literal["low", "medium", "high"], Fuzzy("How severe is this support ticket?")]
    department: Annotated[Department, Fuzzy("Which team should handle this support ticket?")]
    is_outage: Annotated[bool, Fuzzy("The ticket reports a service outage")]


with tab_t:
    st.caption("A `FuzzyModel` with three fields: enum, literal and yes/no. Needs a Jev key.")
    tickets = values_input(
        "t",
        "Site is down for all EU customers since 09:00\nI was charged twice for my March invoice\n"
        "The logo looks blurry on the settings page\ncant log in after password reset",
    )
    if st.button("Triage tickets", type="primary", key="b_t"):
        if not key:
            st.error("Add a Jev API key in the sidebar to run the model-backed fields.")
        else:
            res = Ticket.parse_many(tickets, backend(), threshold)
            rows = [
                {"ticket": t, **{n: (getattr(f.value, "value", f.value)) for n, f in r.fields.items()},
                 **{f"{n} conf": f.confidence for n, f in r.fields.items()}, "needs_review": r.needs_review}
                for t, r in zip(tickets, res)
            ]
            df = pd.DataFrame(rows)
            m1, m2 = st.columns(2)
            m1.metric("Tickets", len(df))
            m2.metric("Need review", int(df.needs_review.sum()))
            st.dataframe(
                df, hide_index=True, width="stretch",
                column_config={**{c: CONF for c in df.columns if c.endswith(" conf")}, "needs_review": FLAG},
            )
