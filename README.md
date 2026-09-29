# dqdqdq

Fuzzy data-quality checks that return **typed values with a confidence score** and flag what
needs human review. Declare a Pydantic-style schema, pass in messy text, and let a fast
decision model ([Jev](https://typesafe.ai)) choose among the allowed values.

```python
from enum import Enum
from typing import Annotated, Literal
from dqdqdq import Fuzzy, FuzzyModel, JevBackend

class Department(str, Enum):
    billing = "billing"
    technical = "technical"

class Ticket(FuzzyModel):
    severity: Annotated[Literal["low", "medium", "high"], Fuzzy("How severe?", threshold=0.9)]
    department: Department
    is_outage: Annotated[bool, Fuzzy("The ticket reports a service outage")]

r = Ticket.parse("Site is down for all EU customers", backend=JevBackend())
r.severity.value, r.severity.confidence   # "high", 0.97
r.value.department                        # Department.technical (validated by Pydantic)
r.needs_review                            # True if any field is under its threshold
```

- `Literal` / `Enum` fields become a Jev *choice* question, `bool` a yes/no probability.
- Exact label matches skip the model call. No backend means unresolved values are flagged.
- Input can be text or a mapping (`{"receipt": ..., "transaction": ...}`); `Fuzzy(source="key")` reads one key.
- `Ticket.parse_many(rows)` dedupes and runs calls concurrently. `Ticket.parse_frame(df, column="text")`
  (or `columns=[...]`) adds value, `_confidence` and `needs_review` columns to a DataFrame.
- Custom types plug in through `Fuzzy(resolver=...)`.

## Add-ons (`dqdqdq.contrib`)
| Add-on | What it does |
|---|---|
| `contrib.countries` (`pip install dqdqdq[countries]`) | messy country text (other languages, typos) to ISO 3166-1 alpha-2/3. Local exact/fuzzy match first, Jev only for the rest. Field type: `Country`. CLI: `dqdqdq countries in.csv -c country -o out.csv` |
| `contrib.currencies` (`dqdqdq[countries]`) | "US dollars", "pesos mx", "€", "Dólar estadounidense" to ISO 4217. Ambiguous symbols like `$` resolve to a best guess with low confidence so they get reviewed. Field type: `Currency` |
| `contrib.units` | "pcs", "piezas", "kilos", "5 lbs" to canonical units (piece, kg, l, ft...), parsing a leading quantity into `detail`. No extra dependencies. Field type: `Unit` |
| `contrib.seniority` | job title + responsibilities to a seniority level, using Jev's ordered `score` question. Field type: `Seniority` |

## Examples
- `examples/ticket_triage.py`: severity, department and outage flag from support tickets.
- `examples/expense_classifier.py`: receipt + bank transaction to category, business flag and a "same purchase?" reconciliation check.
- `examples/order_lines.py`: messy currency and unit columns of purchase-order lines.
- `examples/streamlit_app.py`: country cleaner UI with CSV upload.

## Develop
```bash
uv sync --extra app
uv run pytest
```
Tests use a mock backend; no network or key needed. For Jev, put `TYPESAFE_API_KEY=...` in a
gitignored `.env` file (see `.env.example`).

## Status
See [ROADMAP.md](ROADMAP.md) for what is left to do.

Early. Jev is in early access; `JevBackend(url=...)` is configurable. Roadmap: Polars helper,
`on_low_confidence` hooks, caching, LLM and local backends, benchmarks. Not validated for
decisions about people (hiring, credit, etc.).
