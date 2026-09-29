# dqdqdq

Fuzzy data-quality checks that return **typed values with a confidence score** and flag
what needs human review. Cheap local matching first; a fast decision model
([Jev](https://typesafe.ai)) only for the values local rules can't settle.

First use case: messy country values (other languages, typos, abbreviations) → ISO 3166-1
alpha-2 and alpha-3 codes.

```python
from dqdqdq import resolve_country, JevBackend

resolve_country("Alemania")        # DE / DEU, source="exact", confidence 1.0
resolve_country("Untied States")   # US / USA, source="fuzzy"
resolve_country("la tierra del sol naciente", backend=JevBackend())  # JP / JPN, source="backend"
```

Each result is a `CountryMatch` with `alpha_2`, `alpha_3`, `name`, `confidence`, `source`
and `needs_review` (true when unresolved or below `threshold`, default 0.85).

## pandas and CLI
```python
from dqdqdq import clean_countries, JevBackend
df = clean_countries(df, "country", backend=JevBackend())   # adds alpha_2, alpha_3, confidence, needs_review...
```
```bash
uv run dqdqdq countries in.csv --column country -o out.csv   # add --no-jev for local only
```
Distinct values are resolved once and backend calls run concurrently.

## Second example: ticket triage
`examples/ticket_triage.py` classifies free-text support tickets into severity and department with
`ChoiceField` + `classify_frame`. Any closed label set works the same way.

## Pipeline
1. Exact match on a normalized index (ISO names, translations in ~100 languages, aliases like "USA", "Holland").
2. Fuzzy match (rapidfuzz), accepted only if clearly better than the runner-up country.
3. Optional backend: one Jev `choice` question over all 249 countries (Jev's limit is 255).

## Develop
```bash
uv sync --extra app
uv run pytest
uv run --extra app streamlit run examples/streamlit_app.py
```
Tests use a mock backend; no network or key needed. For Jev, copy `.env.example` to `.env` (gitignored) and set `TYPESAFE_API_KEY`.

## Status
Early. Jev is in early access and its public docs list two base URLs; `JevBackend(url=...)`
is configurable and untested against the live API. Roadmap: `FuzzyModel` schemas, batch/async,
pandas/Polars helpers, caching, LLM and local backends. See `dq-fuzzy-schema-spec.md`.
