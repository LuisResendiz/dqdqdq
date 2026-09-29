# Roadmap / TODO

Status: working prototype. Core `FuzzyModel`, Jev + mock backends, add-ons for countries,
currencies, units and seniority, pandas helper, CLI, Streamlit demo.

## Before a first release
- [x] Name picked: `okayish` (revisit before the first PyPI release: check overlap with `decido`, `jod`, `zod-jev`).
- [ ] Benchmark table: accuracy, latency, cost and share of rows resolved locally, per add-on
      and per backend, on a labelled messy dataset.
- [ ] Publish to PyPI (trusted publishing from GitHub Actions) and tag `v0.1.0`.
- [ ] Verify Jev terms of use for an open-source library that passes users' own keys, and
      rate limits (the API returns 429/529; add retry with backoff).

## Library
- [ ] `on_low_confidence`: raise, return `None`, or call a fallback (human queue).
- [ ] Result caching keyed on input + schema (disk or pluggable store).
- [ ] Polars helper (`parse_frame` for Polars DataFrames).
- [ ] Async API (`aparse`, `aparse_many`).
- [ ] One Jev request per row with several questions instead of one call per field.
- [ ] Retries, timeouts and clear error types for backend failures.
- [ ] `LLMBackend` (provider-agnostic) and a `LocalBackend` (small offline classifier).
- [ ] Fix nested-`Annotated` edge cases and `Optional[...]` fields in `FuzzyModel`.

## Add-ons
- [ ] Units: compound units ("box of 12", "500 ml bottle") are misread as a single unit; consider a
      larger unit table or an optional `pint` integration; per-add-on default thresholds.
- [ ] Currencies: locale-aware `$` and `¥` disambiguation from a neighbouring country/context field.
- [ ] Seniority: live-test the score rubric; add a local alias step for common titles.
- [ ] New ideas: language (ISO 639), US states / ISO 3166-2, industry codes, job families,
      expense categories with merchant lists.

## Examples and docs
- [ ] Ticket-triage and expense examples: tune per-field thresholds (currently too many rows
      flagged for review) and add a labelled evaluation set.
- [ ] Tutorial post and video per example.
- [ ] Hosted Streamlit demo.
- [ ] Not validated for decisions about people (hiring, credit): keep that notice in the README.
