"""Try it: uv run --extra app streamlit run examples/streamlit_app.py"""

import os

import pandas as pd
import streamlit as st

from fuzzschema import JevBackend, resolve_country

st.title("fuzzschema: country cleaner")
key = st.sidebar.text_input("Jev API key (optional)", type="password",
                            value=os.environ.get("TYPESAFE_API_KEY", ""))
threshold = st.sidebar.slider("Review threshold", 0.0, 1.0, 0.85)
backend = JevBackend(api_key=key) if key else None
st.sidebar.caption("Backend: " + ("Jev" if backend else "none (local matching only)"))

raw = st.text_area("One value per line", "Mexico\nAlemania\nUntied States\nドイツ\nla tierra del sol naciente\nWakanda", height=200)
if st.button("Resolve"):
    rows = [resolve_country(v, backend=backend, threshold=threshold)
            for v in raw.splitlines() if v.strip()]
    df = pd.DataFrame([r.__dict__ for r in rows])
    st.dataframe(df.style.apply(lambda r: ["background-color: #5c2b2b" if r.needs_review else "" for _ in r], axis=1))
    st.metric("Need review", int(df.needs_review.sum()))
