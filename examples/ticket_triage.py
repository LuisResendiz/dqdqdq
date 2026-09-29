"""Support-ticket triage: free text -> severity, department, outage flag, with review flags.

uv run python examples/ticket_triage.py
"""

from enum import Enum
from typing import Annotated, Literal

import pandas as pd
from dotenv import load_dotenv

from dqdqdq import Fuzzy, FuzzyModel, JevBackend

load_dotenv()


class Department(str, Enum):
    billing = "billing"
    technical = "technical"
    account = "account"


class Ticket(FuzzyModel):
    severity: Annotated[
        Literal["low", "medium", "high"],
        Fuzzy(
            "How severe is this support ticket?",
            threshold=0.9,
            descriptions={
                "low": "Cosmetic issue or question, no impact on work",
                "medium": "Feature degraded, workaround exists",
                "high": "Service down or data loss, many users affected",
            },
        ),
    ]
    department: Annotated[
        Department,
        Fuzzy(
            "Which team should handle this support ticket?",
            descriptions={
                "billing": "Payments, invoices, refunds, pricing",
                "technical": "Bugs, outages, errors, performance",
                "account": "Login, permissions, profile, cancellations",
            },
        ),
    ]
    is_outage: Annotated[bool, Fuzzy("The ticket reports a service outage")]


tickets = pd.DataFrame(
    {
        "text": [
            "Site is down for all EU customers since 09:00",
            "I was charged twice for my March invoice",
            "The logo looks blurry on the settings page",
            "cant log in after password reset, tried 3 times",
            "Exports crash randomly but re-running works",
        ]
    }
)
backend = JevBackend()
out = Ticket.parse_frame(tickets, column="text", backend=backend)
out["text"] = out["text"].str.slice(0, 32)
print(out.round(2).to_string())
