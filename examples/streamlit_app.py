"""Try it: uv run --extra app streamlit run examples/streamlit_app.py"""

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from dqdqdq import JevBackend
from dqdqdq.contrib.countries import resolve_country

load_dotenv()  # must run before reading the env var below


@st.cache_data(show_spinner=False)
def resolve(value: str, threshold: float, key: str) -> dict:
    backend = JevBackend(api_key=key) if key else None
    return resolve_country(value, backend=backend, threshold=threshold).__dict__


st.title("dqdqdq: country cleaner")
key = st.sidebar.text_input(
    "Jev API key (optional)", type="password", value=os.environ.get("TYPESAFE_API_KEY", "")
)
threshold = st.sidebar.slider("Review threshold", 0.0, 1.0, 0.85)
if key:
    st.sidebar.success("Jev connected")
else:
    st.sidebar.warning("Local only: no Jev key, so hard cases stay unresolved")

upload = st.file_uploader("CSV (optional)", type="csv")
if upload:
    src = pd.read_csv(upload)
    column = st.selectbox("Country column", src.columns)
    values = src[column].astype(str).tolist()
else:
    raw = st.text_area(
        "One value per line",
        "Mexico\nAlemania\nUntied States\nドイツ\nla tierra del sol naciente\nWakanda",
        height=200,
    )
    values = [v for v in raw.splitlines() if v.strip()]

if st.button("Resolve"):
    df = pd.DataFrame([resolve(v, threshold, key) for v in values])
    st.metric("Need review", int(df.needs_review.sum()))
    st.metric("Resolved by Jev", int((df.source == "backend").sum()))
    st.dataframe(
        df.style.apply(
            lambda r: ["background-color: #5c2b2b" if r.needs_review else "" for _ in r], axis=1
        )
    )
    st.download_button("Download CSV", df.to_csv(index=False), "countries_clean.csv")
