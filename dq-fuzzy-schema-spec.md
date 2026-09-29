# Fuzzy schema library for data quality: spec

Working title (pick one): `fuzzmodel`, `softtype`, `tolerant`. Check PyPI and GitHub for name clashes first.

## Goal
Open source, free Python library. You declare a Pydantic-style schema, pass in messy values (free-text cells, log lines, inconsistent labels), and get typed values back with a confidence score. Low-confidence values are flagged instead of silently accepted.

## Why it is different
Tools such as Instructor and Pydantic AI already coerce LLM output into schemas. Those call a slow, costly LLM per value. This library targets row-scale work: fast classification with calibrated confidence, cheap enough to run on every row of a table.

## Scope
- In: constrained fields. Enums, booleans, categorical labels, routing decisions, small typed values.
- Out: free-text generation and rewriting. Jev cannot generate free text and is limited to 255 choices per decision.

## Proposed API (sketch)

```python
from fuzzschema import FuzzyModel, Fuzzy
from typing import Literal

class Ticket(FuzzyModel):
    severity: Fuzzy[Literal["low", "medium", "high"]]
    is_outage: Fuzzy[bool]

result = Ticket.parse("Site is down for all EU customers since 09:00")
result.severity.value       # "high"
result.severity.confidence  # 0.97
result.needs_review         # True if any field is below its threshold
```

- Per-field and global confidence thresholds.
- `on_low_confidence`: raise, return `None`, or call a fallback function (for example, a human queue).
- Batch and async parsing: `parse_many(rows)`, plus a pandas and Polars helper: `df = Ticket.parse_frame(df, column="text")`.
- Result caching keyed on input and schema, to save cost on repeated values.
- Usable inside AWS Lambda and Snowflake UDF-style pipelines (no heavy dependencies).

## Backends (pluggable)
- `JevBackend` (default, fast): TypeSafe's Jev API. Early access, $0.042 per million input tokens. Verify the API, auth and limits before building; the only source so far is the launch blog post.
- `LLMBackend`: any LLM through a provider-agnostic adapter, for people without Jev access.
- `LocalBackend` (later): a small local classifier so it runs fully offline and free.

The backend interface is one method: given text and a set of choices, return the chosen value and a confidence.

## Deliverables
1. Public repo under `LuisResendiz`, MIT or Apache-2.0 license.
2. Package with typed code, tests (mock backend, no network), CI on GitHub Actions, published to PyPI.
3. README with a 30-second quickstart, and a benchmark table: latency, cost and accuracy per backend on the same dataset.
4. Two worked examples: machine-log classification (your Caterpillar-style data) and a support-ticket router.
5. A tutorial post and video for each example, published on the portfolio under projects.

## Milestones
1. Get Jev API access; read the docs; confirm limits and response format.
2. Backend interface and `JevBackend`; parse a single field.
3. `FuzzyModel` with multiple fields, thresholds and review flags.
4. Batch, async and DataFrame helpers, caching.
5. Benchmarks, docs, examples, first release.

## Open questions
- Does Jev accept a set of choices per call, and does it return calibrated confidence per choice or only for the top one?
- Rate limits and terms of use for an open-source library that passes users' own keys.
- Whether the name should imply "fuzzy" or "tolerant" typing.
